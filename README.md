# Build the partner catalog learning lab

This small AWS SAM project creates a **REST API** with `GET /products/{productId}`, a Lambda handler, two API keys, and two usage plans. Both fictional retailers call the **same endpoint**. Different usage targets, not the number of apps calling it, explain the REST API choice.

| Client | Daily quota target | Rate target | Burst capacity |
| --- | ---: | ---: | ---: |
| Retailer A | 100 requests | 2 requests/second | 5 requests |
| Retailer B | 1,000 requests | 5 requests/second | 10 requests |

These are deliberately small learning settings, not production sizing advice. Quotas and throttling are **best effort**; callers can exceed them. They are not a spending cap. API keys identify usage; they are **not authentication or authorization**. The only record is an invented public product, and this lab deliberately has no sign-in or private customer data. A real partner API needs an appropriate authentication and authorization design as well.

AWS SAM means AWS Serverless Application Model. Its template describes resources that AWS CloudFormation creates. Nothing in this package has been deployed.

## What is included

- `template.yaml`: Regional REST API, Lambda integration, two plans and keys, seven-day log retention, cache disabled.
- `src/app.py`: a standard-library-only Python handler with one invented product.
- `tests/test_handler.py`: offline behavior tests.
- `event.json`: an example REST API proxy event for local invocation.

The product data is in a small Python dictionary to keep attention on API selection. It is not a database demonstration. Each route invokes the function only while handling a request; no web server process is kept running by this code.

## 1. Check your account and tools

Use your sandbox account, its available Region, and the current services and plan shown by the new AWS experience. API Gateway, Lambda, CloudFormation, IAM, and CloudWatch permissions must be available to your identity. Availability in the supported-services list does not grant deployment permissions. Ask your coding assistant with Agent Toolkit for AWS to inspect those prerequisites first.

Install Python 3.12, the AWS CLI, and AWS SAM CLI. Authenticate using your chosen AWS profile. These commands use your current CLI profile; add `--profile your-profile` when appropriate.

Check current account benefits and estimated charges before deploying. This project does not promise a particular credit reward. It leaves gateway caching off because an enabled cache has ongoing charges even when requests stop. API calls, Lambda, log storage, and deployment storage can still incur charges.

## 2. Run the offline checks

From this `project` directory:

```bash
python -m unittest discover -s tests -v
sam validate --lint --template-file template.yaml
sam build
```

The Python tests check successful lookup, missing and invalid products, JSON output, and logs that omit incoming headers. They do **not** emulate API Gateway's keys, quotas, deployment, or logging permissions. Those are cloud observations in step 4. If Python 3.12 is not installed locally, SAM can build using Docker with `sam build --use-container`.

Optional local Lambda invocation, with Docker available:

```bash
sam local invoke ProductFunction --event event.json
```

## 3. Review and deploy

Set your available Region explicitly. Replace the placeholder before running:

```bash
EP3_REGION="your-available-region"
EP3_STACK="api-types-partner-lab"

aws sts get-caller-identity --region "$EP3_REGION"

sam deploy --guided \
  --stack-name "$EP3_STACK" \
  --region "$EP3_REGION" \
  --parameter-overrides EnableGatewayAccessLogs=false
```

Review the change set. The function requires an IAM execution role to write logs; SAM creates it. The deployment stores packaged code in an S3 bucket managed or selected by SAM. Save the guided settings if you want to use the update command below.

Gateway access logs start **disabled** because REST API logging requires an API Gateway account setting shared by all REST APIs in that Region. This template does not overwrite that setting. The Lambda handler's minimal logs are available immediately after a successful request. Step 5 explains gateway access logs.

## 4. Call one endpoint as two fictional partners

Read output IDs into variables. Key values are intentionally absent from stack outputs:

```bash
ep3_output() {
  aws cloudformation describe-stacks \
    --stack-name "$EP3_STACK" --region "$EP3_REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" \
    --output text
}

EP3_URL=$(ep3_output ProductUrl)
EP3_KEY_A_ID=$(ep3_output RetailerAKeyId)
EP3_KEY_B_ID=$(ep3_output RetailerBKeyId)

EP3_KEY_A=$(aws apigateway get-api-key \
  --api-key "$EP3_KEY_A_ID" --include-value \
  --region "$EP3_REGION" --query value --output text)

EP3_KEY_B=$(aws apigateway get-api-key \
  --api-key "$EP3_KEY_B_ID" --include-value \
  --region "$EP3_REGION" --query value --output text)
```

Keep these values in your local session. Do not put them in screenshots, source control, or public frontend code. For a real retailer integration, the retailer's backend would hold its integration credentials and usage key.

```bash
# Missing key: expect a gateway 403 response, before Lambda runs.
curl -i "$EP3_URL"

# Valid keys: both partners receive the same product data.
curl -i -H "x-api-key: $EP3_KEY_A" "$EP3_URL"
curl -i -H "x-api-key: $EP3_KEY_B" "$EP3_URL"

# Valid key, nonexistent product: the handler returns 404.
curl -i -H "x-api-key: $EP3_KEY_A" "${EP3_URL%1738}9999"
```

Successful response body:

```json
{"productId":"1738","name":"Everyday Headphones","price":79.99,"currency":"USD"}
```

New API-key associations can take a few minutes to propagate. If a valid key initially receives 403, confirm its plan includes this API's `dev` stage, then retry after propagation. Avoid rapid loops: a 429 means a throttling or quota target may have been reached, and exact cutoff timing is not guaranteed.

In the API Gateway console, open **Usage plans**, choose each plan, and inspect **Associated API keys** and usage. Each plan applies to the same API and stage. If both keys belonged to one shared plan, they would each receive the same configured target, with usage counted separately. Here, two plans make the different target values explicit.

## 5. Follow a request through logs

First, see successful handler requests in its log group:

```bash
EP3_FUNCTION_LOGS=$(ep3_output FunctionLogGroupName)
aws logs tail "$EP3_FUNCTION_LOGS" \
  --since 10m --region "$EP3_REGION"
```

Look for `requestId`, `operation: productLookup`, and `status`. A missing API key is rejected before the integration, so it will not produce this handler entry. That is a useful reason to add gateway access logs: they also record requests that never reach Lambda.

Check whether the API Gateway regional logging role is already configured:

```bash
aws apigateway get-account --region "$EP3_REGION" \
  --query cloudwatchRoleArn --output text
```

If a valid role is present, reuse it. If the result is empty or `None`, have the account owner configure the role using the API Gateway **Settings** page in this Region. The IAM role trusts `apigateway.amazonaws.com`, has the `AmazonAPIGatewayPushToCloudWatchLogs` managed policy, and its ARN is set as API Gateway's CloudWatch log role ARN. AWS STS must be enabled in that Region. This is an account-level setting, so coordinate with other API owners rather than replacing an existing role. The [AWS logging guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html) describes it.

Once logging permissions work, update the stack using your saved guided settings:

```bash
sam deploy \
  --stack-name "$EP3_STACK" --region "$EP3_REGION" \
  --parameter-overrides EnableGatewayAccessLogs=true
```

Repeat a request with a valid key and one without. Then:

```bash
EP3_GATEWAY_LOGS=$(ep3_output GatewayAccessLogGroupName)
aws logs tail "$EP3_GATEWAY_LOGS" \
  --since 10m --region "$EP3_REGION"
```

The access log records request IDs, the route template, method, status, response time, and the **API key ID**. It does not record the key value, token, request body, or client IP address. Match the gateway `requestId` with the handler's `requestId` for a forwarded request. A 403 before integration has a gateway entry but no handler entry. Logs can take a short time to arrive.

## 6. Explain what you observed

1. Why do both retailers receive the same data despite different plans?
2. Why can a missing key produce 403 without the function running?
3. Why does a valid key not prove that a shopper signed in?
4. What evidence distinguishes a gateway rejection from a handler's 404?
5. If there were no usage-plan requirement, could an HTTP API serve these same two retailers? Yes. The distinguishing requirement is built-in per-key usage controls.
6. Why would you avoid using the quota as your budget alarm or a hard security boundary?

Do not load-test to prove an exact quota cutoff. Reading the configured plans, making a few requests, and inspecting usage teaches the concept with less traffic. Treat a 429 as a retry signal; a production client should use backoff rather than retrying immediately.

## 7. Clean up

From the same project directory:

```bash
sam delete --stack-name "$EP3_STACK" --region "$EP3_REGION"
unset EP3_KEY_A EP3_KEY_B
```

Review SAM's cleanup prompts, including packaged S3 artifacts. Confirm the stack and its API, Lambda function, keys, usage plans, and log groups are removed. This template deletes its log groups rather than retaining them. A logging role configured separately in the regional API Gateway account settings is shared infrastructure: do not delete it while other APIs use it. Remove any extra resources you created in optional experiments, including an enabled cache.

## Scope and validation

This is a teaching starter with fictional data, not a production partner platform. It does not create a database, frontend, authorizer, WebSocket chat, cache cluster, or custom domain. It tests the REST API feature that motivated the choice. No AWS resources were created while preparing this package.

Package checks on October 12, 2026: five offline tests passed under Python 3.12.14; the SAM template passed `cfn-lint` 1.57.2 with no findings. Cloud deployment, API key propagation, and account-specific logging permissions still need verification in your own account.

Current primary references:

- [AWS SAM API resource](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-api.html)
- [AWS API keys and usage plans](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)
- [API keys and plans with CloudFormation](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-key-usage-plan-cfn.html)
- [Supported services in the new signup experience](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-free-tier)
