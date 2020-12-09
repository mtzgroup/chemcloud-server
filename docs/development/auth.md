# Authentication and Authorization

## Choices and Justifications

- Auth is complicated. We do not want to roll our own auth servers. We are using [Auth0](https://auth0.com) as our Authentication Server and will follow [OAuth 2.0](https://oauth.net/2/) protocols for authentication.
- Read up on FastAPI's [Security](https://fastapi.tiangolo.com/tutorial/security/) and [Advanced Security](https://fastapi.tiangolo.com/advanced/security/) documentaion to better understand how to implement OAuth2 flows in FastAPI.
- Because many users will be interacting with TeraChem Cloud via Python code directly, we
