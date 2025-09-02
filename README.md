# AWS AI Photo Album Web Application

An end‑to‑end, serverless photo album that uses **Amazon Rekognition** to auto‑tag images, **Amazon OpenSearch Service** to index/search them, and **Amazon Lex (v2)** to interpret natural‑language queries. A lightweight web frontend lets you **upload photos (with optional custom labels)**, **search by text or voice**, and view results.


## What this app does

1. **Upload photos** via a simple web UI. You can optionally attach **custom labels** (e.g., `wedding, family, 2021`).
2. A **PUT /upload** API Gateway route writes your file into S3 **with the `x-amz-meta-customlabels` header** preserved.
3. An S3 **ObjectCreated** event triggers a Lambda function (**index-photos**) that:
   - Calls **Amazon Rekognition** to detect labels.
   - Merges Rekognition labels with any **custom labels** from S3 object metadata.
   - Indexes a photo document into **Amazon OpenSearch Service** (`photos` index) with fields like `objectKey`, `bucket`, `createdTimestamp`, and `labels`.
4. Users search with **text or voice**:
   - The frontend calls **GET /search?q=...**.
   - A Lambda function (**search-photos**) uses **Lex v2** to extract label terms from natural language (e.g., “pictures of dogs on the beach” → `dog, beach`), normalizes them (singularization), then queries **OpenSearch**.
   - Results are returned with an **image URL** and label metadata for display in the UI.

## Architecture (high level)

- **Frontend**: Static HTML/JS/CSS (no build step). Supports voice search via the **Web Speech API** (Chrome/Edge).  
- **API Gateway**: 
  - `GET /search?q=<query>` → **search-photos** Lambda.
  - `PUT /upload/{bucket}/{filename}` → S3 proxy (passes **`x-amz-meta-customLabels`** to the object’s metadata).
- **S3**: Photo storage. Triggers indexing Lambda on upload.
- **Lambda (Python)**:
  - **index-photos.py**: Extracts labels with Rekognition; writes documents to **OpenSearch**.
  - **search-photos.py**: Runs **Lex v2** query interpretation; searches **OpenSearch** and formats results.
- **Amazon Rekognition**: Label detection.
- **Amazon OpenSearch Service**: Index `photos` storing metadata and label arrays; searched by terms.
- **Amazon Lex v2**: Interprets free‑form queries and surfaces label slot values.


## Repository layout

```
.
├─ Lambda/
│  ├─ index-photos.py        # S3-triggered indexer; Rekognition + OpenSearch
│  └─ search-photos.py       # Lex v2 + OpenSearch query; returns image metadata
├─ frontend/
│  ├─ index.html             # Simple UI: search, voice search, upload
│  ├─ app.js                 # Calls API Gateway, handles uploads, renders results
│  └─ styles.css             # Minimal styling
├─ AI Photo Search-test-stage-swagger.yaml   # Swagger for API Gateway (search & upload)
├─ PhotoWebCF.yaml           # Draft CloudFormation for core resources (incomplete/example)
└─ README.md
```

## Frontend

The frontend is plain HTML + JavaScript and can be hosted from **any static web host** (e.g., S3 static website hosting or CloudFront). It provides:
- **Search**: GET `/search?q=<text>`
- **Voice Search**: via `webkitSpeechRecognition` (Chrome/Edge)
- **Upload**: PUT `/upload/{bucket}/{filename}` with header `x-amz-meta-customLabels: comma,separated,labels`

### Change API endpoints
Open `frontend/app.js` and replace the example API base:
```js
fetch(`https://<your-api-id>.execute-api.<region>.amazonaws.com/<stage>/search?q=${query}`)
fetch('https://<your-api-id>.execute-api.<region>.amazonaws.com/<stage>/upload/<your-photo-bucket>/' + photo.name, { ... })
```

## API

The included Swagger (`AI Photo Search-test-stage-swagger.yaml`) defines two routes:

### `GET /search`
- **Query**: `q` (string) — arbitrary natural language.
- **Response**: `200 OK` with an array of objects like:
  ```json
  [
    {
      "objectKey": "IMG_001.jpg",
      "bucket": "my-photo-bucket",
      "createdTimestamp": "2025-09-02T18:00:00Z",
      "labels": ["dog", "beach", "outdoors"],
      "imageUrl": "https://my-photo-bucket.s3.amazonaws.com/IMG_001.jpg"
    }
  ]
  ```

### `PUT /upload/{bucket}/{filename}`
- **Headers** (optional): `x-amz-meta-customLabels: label1,label2,label3`
- **Body**: raw image bytes (`Content-Type` should match the file type)
- **Effect**: Stores object to S3 with custom metadata. S3 event triggers indexing Lambda.


## Lambda configuration

Both Lambdas are Python and use the following libraries/services:

- `boto3` (S3, Rekognition, Lex v2 Runtime)
- `opensearch-py`
- `requests-aws4auth`
- `inflection` (for singularization of labels)

### Required environment/config values
Set these as **Lambda environment variables** (recommended) or inline constants:

- `REGION` — e.g., `us-east-1`
- `OPENSEARCH_HOST` — your OpenSearch **domain endpoint**, e.g. `search-photos-abc123.us-east-1.es.amazonaws.com`
- `OPENSEARCH_INDEX` — `photos` (default in this repo)
- **Lex v2 (search-photos Lambda)**: define one of the following:
  - Hard‑code your bot details in code, **or** provide env vars:
    - `LEX_BOT_ID`
    - `LEX_BOT_ALIAS_ID`
    - `LEX_LOCALE_ID` (e.g., `en_US`)

### IAM permissions (minimum)
- **index-photos Lambda**: `rekognition:DetectLabels`, `s3:GetObject`, `es:ESHttp*` (scoped to your domain), CloudWatch Logs.
- **search-photos Lambda**: `lex:RecognizeText` (or equivalent v2 runtime API), `es:ESHttp*`, CloudWatch Logs.

## OpenSearch index mapping (suggested)

Create the index before first use or let the Lambda create it lazily. A simple mapping:

```json
PUT /photos
{
  "mappings": {
    "properties": {
      "objectKey": { "type": "keyword" },
      "bucket":    { "type": "keyword" },
      "createdTimestamp": { "type": "date" },
      "labels":    { "type": "keyword" }
    }
  }
}
```

The **search** Lambda performs **term/terms** queries on `labels` (after Lex normalization). You can expand this to n‑grams or text fields if you want fuzzy matching.


## Deploy

1. **Create an S3 bucket** for photos (e.g., `my-photo-bucket`).
2. **Create an OpenSearch domain** and note its **endpoint**.
3. **Create a Lex v2 bot** with slots for labels (e.g., `Label1`, `Label2`) or a simple intent that returns `interpretedValue` tokens. Publish an **alias** and note `BotId`, `BotAliasId`, and `LocaleId`.
4. **Create the Lambdas**:
   - Package dependencies (`opensearch-py`, `requests-aws4auth`, `inflection`) with your code (or use layers).
   - Set environment variables (see above).
   - Attach IAM roles with least‑privilege policies.
5. **S3 trigger**: Configure the **index-photos** Lambda to run on `s3:ObjectCreated:*` for your photo bucket.
6. **API Gateway**:
   - Import the provided Swagger.
   - Wire `GET /search` to the **search-photos** Lambda (Lambda proxy or integration request mapping).
   - Configure `PUT /upload/{bucket}/{filename}` as an **S3 proxy** that forwards `x-amz-meta-customLabels`.
   - Enable CORS for both routes.
7. **Frontend**:
   - Update `frontend/app.js` with your API base URL and bucket name.
   - Host `frontend/` on S3 static hosting or any static host.

## Using the app

- **Upload**: Pick an image and (optionally) enter custom labels → Upload. Wait a moment for S3 → Lambda → Rekognition → OpenSearch indexing.
- **Search**: Type natural language (e.g., _“photos of cats indoors”_) or click **Voice Search**. Results show thumbnails with their labels.
