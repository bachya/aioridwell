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
    addOnEstimatedCents
    itemizedAvailableCredits {
      creditCategory
      amountCents
      __typename
    }
    __typename
  }
}
"""

QUERY_SUBSCRIPTION_PICKUPS = """
query upcomingSubscriptionPickups($subscriptionId: ID!) {
  upcomingSubscriptionPickups(subscriptionId: $subscriptionId) {
    ...SubscriptionPickupData
    __typename
  }
}

fragment SubscriptionPickupData on SubscriptionPickup {
  id
  type
  state
  pickupOn
  schedulabilityState
  selectedFeaturedOffer {
    id
    sanityId
    __typename
  }
  pickupOffers {
    id
    sanityId
    endOn
    type
    isAutoOptIn
    category {
      slug
      __typename
    }
    __typename
  }
  pickupProductSelections {
    pickupOfferPickupProduct {
      pickupOffer {
        id
        sanityId
        endOn
        type
        isAutoOptIn
        priority
        category {
          name
          __typename
        }
        __typename
      }
      pickupProduct {
        id
        __typename
      }
      __typename
    }
    quantity
    __typename
  }
  __typename
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
