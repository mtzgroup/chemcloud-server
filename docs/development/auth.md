# Authentication and Authorization

## Choices and Justifications

- Auth is complicated. We do not want to roll our own auth servers. We are using [Auth0](https://auth0.com) as our Authentication Server and will follow [OAuth 2.0](https://oauth.net/2/) protocols for authentication.
- Read up on FastAPI's [Security](https://fastapi.tiangolo.com/tutorial/security/) and [Advanced Security](https://fastapi.tiangolo.com/advanced/security/) documentation to better understand how to implement OAuth2 flows in FastAPI.
- We are using Auth0's [Role Based Access Control (RBAC)](https://auth0.com/docs/authorization/rbac) to manage permissions for users in Auth0 combined this with [FastAPI's scopes api](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/) to protect endpoints.
- Upon user signup, each new users is automatically assigned to the role of "Public User" using an Auth0 rule. This assigns them the basic permission `compute:public` which is the minimum permission required to submit compute jobs to TeraChem Cloud and retrieve results.
- It is anticipated that `compute:private` will be the permission assigned to users, along with user metadata about the queues to which they can submit jobs, that will enable a user to submit jobs to private compute instances not available to public users.
