import json
import boto3
import inflection
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime')

# OpenSearch configuration
OPENSEARCH_HOST = 'search-photos-qwdpz3oledsvjph5kld7afjoqq.us-east-1.es.amazonaws.com'
OPENSEARCH_INDEX = 'photos'
REGION = 'us-east-1'

def lambda_handler(event, context):
    
    print('event',event)
    
    q = event['q']
    print('q', q)
    
    labels = get_labels(q)
    print('labels',labels)
    
    singular_labels = []
    
    for label in labels:
        label = inflection.singularize(label)
        singular_labels.append(label)
        
    print(singular_labels)
    
    if singular_labels:
        results = search_opensearch(singular_labels)
        print('results',results)
        
        image_results = []
        for result in results:
            image_url = f'https://coms6998-asm-2.s3.amazonaws.com/{result["objectKey"]}'
            
            image_result = {
                "objectKey": result["objectKey"],
                "bucket": result["bucket"],
                "createdTimestamp": result["createdTimestamp"],
                "labels": result["labels"],
                "imageUrl": image_url
            }
            
            image_results.append(image_result)
            
        print('image_results',image_results)
            
        response = {
            'statusCode': 200,
            'body': image_results
        }
        
    else:
        # No labels, return an empty array
        # results = []
        
        response = {
            'statusCode': 200,
            'body': []
        }
        
    # results = []
    print('response',response)
    
    return response


    
    # slots = event["sessionState"]["intent"]["slots"]
    
    # labels = []
    
    # if slots["Label1"] and slots["Label1"]["value"] and slots["Label1"]["value"]["interpretedValue"]:
    #     labels.append(slots["Label1"]["value"]["interpretedValue"])
    
    
    # if slots["Label2"] and slots["Label2"]["value"] and slots["Label2"]["value"]["interpretedValue"]:
    #     labels.append(slots["Label2"]["value"]["interpretedValue"])
        
    # print('labels',labels)
    
    # # Extract the query string from the Lex event
    # query = event['queryStringParameters']['q']
    
    # # Get labels using Lex disambiguation request
    # labels = get_lex_labels(query)
    
    # # If there are labels, perform OpenSearch search
    # if labels:
    #     results = search_opensearch(labels)
    # else:
    #     # No labels, return an empty array
    #     results = []

    # Return results according to the API spec
    # return {
    #     'statusCode': 200,
    #     'body': json.dumps(results)
    # }
    
    
def search_opensearch(labels):
    # TODO: Use OpenSearch SDK to perform search in the "photos" index
    # This may involve creating OpenSearch connection and executing a query
    
    # lab = ['building']
    
    q = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"labels": label}} for label in labels
                    ]
                }
            }
        }
            
    # print('q',q)
    
    opensearch = OpenSearch(
        hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
        http_auth=get_awsauth(REGION, 'es'),
        connection_class=RequestsHttpConnection,
        use_ssl=True,
        verify_certs=True,
    )
    
    # print('opensearch',opensearch)
    
    try:
        response = opensearch.search(index=OPENSEARCH_INDEX,body=q)
        
        
        hits = response['hits']['hits']
        print('hits', hits)
        
        # Extract relevant information from the OpenSearch response
        results = [hit["_source"] for hit in response["hits"]["hits"]]
        
    except Exception as e:
        # Handle any errors that may occur during the OpenSearch search
        print(f"Error searching in OpenSearch: {e}")
        results = []
        
    return results
    
def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key, cred.secret_key, region, service, session_token=cred.token)



def get_labels(query):

    lex_response = client.recognize_text(
        botId='7YNIXP06QQ', # MODIFY HERE
        botAliasId='TSTALIASID', # MODIFY HERE
        localeId='en_US',
        sessionId='testuser',
        # text=msg_from_user
        text=query
    )
    
    print("lex-response", lex_response)

    # Extract labels from the Lex response
    labels = []
    
    # if 'slots' not in lex_response:
    #     print("No photo for query {}".format(query))
    # else:
    #     print ("slots: ",lex_response['slots'])
    #     slot_val = lex_response['slots']
    #     labels.extend(lex_response['slots'].values())
        
        
        
    if 'intent' in lex_response['sessionState']:
        intent = lex_response['sessionState']['intent']

        if 'slots' in intent:
            print("Slots: ", intent['slots'])
            slots = intent['slots']
            
            
            if "Label1" in slots and slots["Label1"] and slots["Label1"]["value"] and slots["Label1"]["value"]["interpretedValue"]:
                labels.extend(slots["Label1"]["value"]["interpretedValue"].split())
    
    
            if "Label2" in slots and slots["Label2"] and slots["Label2"]["value"] and slots["Label2"]["value"]["interpretedValue"]:
                labels.extend(slots["Label2"]["value"]["interpretedValue"].split())
                
                
            # labels.extend(intent['slots'].values())
            
            
            
        else:
            print("No slots found.")

            
            
    else:
        print("No intent found.")
        
    return labels

    # # Extracting slots or other relevant information from Lex response
    # # This is a simplified example; you may need to adapt it based on your Lex bot design
    # if 'slots' in lex_response:
    #     labels.extend(lex_response['slots'].values())

    # return labels

    
    # labels = []
    # if 'slots' not in response:
    #     print("No photo collection for query {}".format(query))
    # else:
    #     print ("slot: ",response['slots'])
    #     slot_val = response['slots']
    #     for key,value in slot_val.items():
    #         if value!=None:
    #             labels.append(value)
    # return labels
    
# def get_lex_labels(event):
#     slots = event["sessionState"]["intent"]["slots"]
    
#     labels = []
    
#     if slots["Label1"] and slots["Label1"]["value"] and slots["Label1"]["value"]["interpretedValue"]:
#         labels.append(slots["Label1"]["value"]["interpretedValue"])
    
    
#     if slots["Label2"] and slots["Label2"]["value"] and slots["Label2"]["value"]["interpretedValue"]:
#         labels.append(slots["Label2"]["value"]["interpretedValue"])
        
#     print('labels',labels)
    
#     return labels
    
    
    
    
#     # Use Amazon Lex bot for query disambiguation, return a list of labels
#     # This may involve calling Lex runtime or management API

#     # Replace 'YourBotName' and 'YourBotAlias' with your Lex bot name and alias
#     # bot_name = 'YourBotName'
#     # bot_alias = 'YourBotAlias'
    
#     # Initialize the Lex Runtime client
#     client = boto3.client('lexv2-runtime')

#     # Call the PostText operation to send the query to Lex
#     lex_response = lex_runtime.post_text(
#         botName=bot_name,
#         botAlias=bot_alias,
#         userId='user',  # Replace with a user identifier
#         inputText=query
#     )
    
    
#     lex_response = client.recognize_text(
#         botId='7YNIXP06QQ', # MODIFY HERE
#         botAliasId='TSTALIASID', # MODIFY HERE
#         localeId='en_US',
#         sessionId='testuser',
#         # text=msg_from_user
    #     text=query
    # )

    # # Extract labels from the Lex response
    # labels = []

    # # Extracting slots or other relevant information from Lex response
    # # This is a simplified example; you may need to adapt it based on your Lex bot design
    # if 'slots' in lex_response:
    #     labels.extend(lex_response['slots'].values())

    # return labels


# def search_opensearch(labels):
    # TODO: Use OpenSearch SDK to perform search in the "photos" index
    # This may involve creating OpenSearch connection and executing a query
    
    

