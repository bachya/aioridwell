"""Define query strings used by the Ridwell API."""
QUERY_ACCOUNT_DATA = """
query user($id: ID!) {
  user(id: $id) {
    fullName
    email
    phone
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
      }
    }
  }
}
"""

QUERY_AUTH_DATA = """
mutation createAuthentication($input: CreateAuthenticationInput!) {
  createAuthentication(input: $input) {
    authenticationToken
  }
}
"""

QUERY_SUBSCRIPTION_PICKUP_QUOTE = """
query subscriptionPickupQuote($input: SubscriptionPickupQuoteInput!) {
  subscriptionPickupQuote(input: $input) {
    totalCents
  }
}
"""

QUERY_SUBSCRIPTION_PICKUPS = """
query upcomingSubscriptionPickups($subscriptionId: ID!) {
  upcomingSubscriptionPickups(subscriptionId: $subscriptionId) {
    id
    state
    pickupOn
    pickupProductSelections {
      pickupOfferPickupProduct {
        pickupOffer {
          id
          priority
          category {
            name
          }
        }
        pickupProduct {
          id
        }
      }
      quantity
    }
  }
}
"""

QUERY_UPDATE_SUBSCRIPTION_PICKUP = """
mutation updateSubscriptionPickup($input: UpdateSubscriptionPickupInput!) {
  updateSubscriptionPickup(input: $input) {
    subscriptionPickup {
      id
      type
      state
      pickupOn
    }
  }
}
"""
