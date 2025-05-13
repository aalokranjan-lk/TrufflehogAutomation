## 🔐 Zoho CRM - Refresh Access Token Using cURL

To generate a new access token using a refresh token for Zoho CRM, use the following `curl` command:

```bash
curl --request POST 'https://accounts.zoho.com/oauth/v2/token' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'refresh_token=1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
  --data-urlencode 'client_id=1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
  --data-urlencode 'client_secret=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
  --data-urlencode 'grant_type=refresh_token'
```
```bash
curl --request GET 'https://www.zohoapis.com/crm/v4/organizations' \
  --header 'Authorization: Zoho-oauthtoken 1000.6d169c711fce258ec896******************'
```

## ✅ AWS S3 Credential Validation

### 1. Configure
```bash
aws configure
```
### ✅ AWS S3 Credential Validation

### 1. Configure
```bash
aws configure

aws s3 ls
```

## Stripe 

```
curl https://api.stripe.com/v1/account \
  -u sk_live_3WUO1sYdZt*********:
``` 
