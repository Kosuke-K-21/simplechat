# lambda/index.py
import json
import os
import urllib.request
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値


def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # 会話履歴を含める
        prompt = ""
        for msg in messages:
            if msg["role"] == "user: ":
                prompt += "## user: "
            elif msg["role"] == "## assistant: ":
                bedrock_messages.append({
                    "role": "assistant", 
                    "content": [{"text": msg["content"]}]
                })
            prompt += msg["content"] + "\n"
        
        prompt += "## assistant: "
        
        # invoke_model用のリクエストペイロード
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        print("Calling API with payload:", json.dumps(request_payload))

        # invoke_model APIを呼び出し
        response = urllib.request.Request(
            url="https://2e20-34-87-23-130.ngrok-free.app/generate",
            data=json.dumps(request_payload).encode(),
            headers={
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(response) as res:
            response_body = res.read()
            response_body = json.loads(response_body.decode('utf-8'))

        # 応答の検証
        if not response_body.get('generated_text'):
            raise Exception("No response content from the model")


        generated_text = response_body.get('generated_text')
                        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": generated_text
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": generated_text,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }