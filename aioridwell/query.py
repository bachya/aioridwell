"""Define query strings used by the Ridwell API."""
QUERY_CREATE_AUTHENTICATION = """
mutation createAuthentication($input: CreateAuthenticationInput!) {
  createAuthentication(input: $input) {
    authenticationToken
  }
}
"""

QUERY_SUBSCRIPTION_DATA = """
query user($id: ID!) {
  user(id: $id) {
    accounts {
      id
      address {
        street1
        city
        subdivision
        postalCode
      }
      activeSubscription {
        id
        state
        futureSubscriptionPickups {
          startOn
          pickupOffers {
            category {
              slug
            }
          }
        }
      }
    }
  }
}
"""

QUERY_USER_DATA = """
query user($id: ID!) {
  user(id: $id) {
    id
    fullName
    email
    phone
  }
}
"""
