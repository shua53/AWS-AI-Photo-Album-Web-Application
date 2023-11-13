import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Create AWS S3 and Rekognition instances
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

# OpenSearch configuration
OPENSEARCH_HOST = 'search-photos-qwdpz3oledsvjph5kld7afjoqq.us-east-1.es.amazonaws.com'
OPENSEARCH_INDEX = 'photos'
REGION = 'us-east-1'

def lambda_handler(event, context):
    
    print('event',event)
    
    # Get information about the S3 bucket and object for the uploaded photo
    bucket = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    try:
        # Use Rekognition's detectLabels method to detect labels in the photo
        response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': object_key
                }
            }
        )
        
        print('response',response)

        # Use S3 SDK's headObject method to retrieve the metadata of the object
        metadata_response = s3.head_object(
            Bucket=bucket,
            Key=object_key
        )
        
        print('metadata_response',metadata_response)

        # Get the x-amz-meta-customLabels metadata field
        custom_labels = metadata_response.get('Metadata', {}).get('customlabels', '').split(',')
        
        print('custom_labels',custom_labels)

        # Build the JSON object
        photo_data = {
            'objectKey': object_key,
            'bucket': bucket,
            'createdTimestamp': metadata_response['LastModified'].isoformat(),
            'labels': custom_labels + [label['Name'] for label in response['Labels']]
        }
        
        print('photo_data',photo_data)

        
        client = OpenSearch(hosts=[{
            'host': OPENSEARCH_HOST,
            'port': 443
        }],
                            http_auth=get_awsauth(REGION, 'es'),
                            use_ssl=True,
                            verify_certs=True,
                            connection_class=RequestsHttpConnection)
    
        store = client.index(index=OPENSEARCH_INDEX, body=photo_data)
        print('store',store)
        

        # result = client.get(index='photos', id='zs6vw4sBgiFjxwEIyDow')
        # print('document_content',result['_source'])
        # client.delete(index='photos', id='2M66xIsBgiFjxwEI1DoL')
        
        
        # query = {
        #     "query": {
        #         "match_all": {}
        #     }
        # }
        
        # response = client.search(index=OPENSEARCH_INDEX, body=query)
        

        # document_ids = [hit["_id"] for hit in response["hits"]["hits"]]
        # print('document_ids',document_ids)
        
        # # Assuming you have a list of document IDs in document_ids
        # for document_id in document_ids:
        #     # Fetch document by ID
        #     document_response = client.get(index=OPENSEARCH_INDEX, id=document_id)
            
        #     # Extract and print the document content
        #     document_content = document_response["_source"]
        #     print(f"Document ID: {document_id}, Content: {document_content}")


        # document_content = result['_source']
        # print(document_content)

        # Return a success response
        return {
            'statusCode': 200,
            'body': 'Indexing completed successfully'
        }
    except Exception as e:
        print("Error indexing photo:", str(e))
        return {
            'statusCode': 500,
            'body': "Error indexing photo"
        }
        
        
def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key, cred.secret_key, region, service, session_token=cred.token)
