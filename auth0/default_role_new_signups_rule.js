// This rule assigns a default role found on the Auth0 configuration object
// at configuration.AUTH0_PUBLIC_USER_ROLE_ID to all new users upon signup.

function (user, context, callback) {
    const ManagementClient = require('auth0@2.27.0').ManagementClient;

  const management = new ManagementClient({
    token: auth0.accessToken,
    domain: auth0.domain
  });

    console.log(auth0.accessToken);
  const count = context.stats && context.stats.loginsCount ? context.stats.loginsCount : 0;
  if (count > 1) {
      return callback(null, user, context);
  }

  const params =  { id : user.user_id};
  const data = { "roles" : [configuration.AUTH0_PUBLIC_USER_ROLE_ID]};

  management.users.assignRoles(params, data, function (err, user) {
    if (err) {
      // Handle error.
      console.log(err);
    }
      console.log("success");
  callback(null, user, context);
  });
  
}