# Guide: calls

Version: v2. Read `common.md` first.

This guide has eight labels. Each asks whether the post **asks its readers to do something**, and what. A post can get several `yes`, or none.

## Shared condition C: the post makes a request

Every label of this guide needs condition C. C is met when the post contains at least one of these forms, aimed at its readers or at people in general:

| Form | Examples |
| --- | --- |
| (a) An imperative | "Share this", "Vote them out", "Join us" |
| (b) An exhortation that includes the author | "Let's …", "We must …", "We need to …", "Time to …" |
| (c) An obligation put on readers or on people in general, active or passive | "You should …", "Everyone must …", "Someone should …", "They should all be …" |
| (d) A request or an invitation | "Please …", "Can you …", "Help us …", "Who's coming?" |
| (e) An event with a time or a place and an invitation | "Saturday 2pm, City Hall. Be there" |
| (f) A hashtag that is itself one of the forms above | `#BoycottAcme`, `#VoteThemOut` |

C is **not** met by:

- a demand aimed at an authority or at the target itself: "The minister must resign", "@Acme fix this now";
- a wish or a forecast: "I hope people stop buying this", "They will be voted out";
- the author's own act or plan: "I'm going to the march", "I just signed";
- a report that others ask for it: "Unions call for a strike" (rule 3 of `common.md`).

If C is not met, answer `no` to all eight labels.

Evidence for every label of this guide: required. Quote the span that holds the request.

## `call_amplify`

**Question.** Does the post ask readers to spread a message?

**YES when both are true:**

1. C is met.
2. What is asked is to spread content: repost, retweet, share, quote, copy and paste, tag or mention accounts, use or push a hashtag, make something trend, "spread the word", "tell everyone".

**NO when:**

- only a like, a follow or a subscription is asked;
- only reading or watching is asked ("read this thread");
- a hashtag is present but nobody is asked to use it. A campaign hashtag (`#StandWithAcme`, `#SaveTheLibrary`) is not by itself a request to spread.

**Examples.**

- YES: "Everyone needs to see this. RT!" → `RT!`
- YES: "Copy and paste this on your profile, don't just like it" → `Copy and paste this on your profile`
- NO: "This video is going viral, 2M shares already" (a report)
- NO: "Follow me for daily updates" (a follow)
- NO: "So tired of this #election" (no request)

## `call_pressure`

**Question.** Does the post ask readers to act on a named target to make it yield?

**YES when all are true:**

1. C is met.
2. What is asked is one of: contact the target (call, email, write, message, "tell @X"), report an account or a post, flood replies or comments, leave reviews, file complaints, sign a petition.
3. The target is named or pointed at: a name, an `@name`, "this account", "your MP", "your representative", the addressee of a petition.

**NO when:**

- the author addresses the target directly and asks nobody else ("@Acme, shame on you");
- readers are asked to tell friends or followers (that is `call_amplify`);
- readers are asked to stop buying (that is `call_boycott`).

**Examples.**

- YES: "Call your senator today and tell them to vote no" → `Call your senator today`
- YES: "Everyone report this account, it's spreading lies" → `Everyone report this account`
- YES: "Sign the petition to save the library" → `Sign the petition`
- NO: "@CityCouncil you should be ashamed" (direct address, no request to readers)
- NO: "Thousands signed the petition against the airport" (a report)

## `call_protest`

**Question.** Does the post ask readers to take part in a physical collective action?

**YES when both are true:**

1. C is met.
2. What is asked is to demonstrate, march, rally, gather, strike, walk out, occupy, block, or "take to the streets".

**NO when:**

- the action is online only;
- the action is voting, buying or not buying;
- the author only says they will go, or reports a protest.

**Examples.**

- YES: "General strike on Monday. Stay home, shut it all down" → `Stay home, shut it all down`
- YES: "Saturday 2pm at City Hall. Bring signs, bring friends" → `Bring signs, bring friends`
- NO: "Huge crowd at the march today, proud to be here" (the author's own act)
- NO: "Farmers block the motorway for the third day" (a report)

## `call_boycott`

**Question.** Does the post ask readers to stop buying from, using or funding a named target?

**YES when all are true:**

1. C is met.
2. What is asked is to stop buying, using, watching, subscribing to or funding something: boycott, cancel, unsubscribe, delete the app, "don't give them a cent".
3. The target is named: a brand, a company, a person, an outlet, a country, an event.

**NO when:**

- no target is named ("don't buy cheap chargers");
- the author only says they stopped ("I cancelled my subscription").

**Examples.**

- YES: "Cancel your Acme subscription today. Hit them where it hurts" → `Cancel your Acme subscription today`
- YES: "#BoycottAcme" → `#BoycottAcme`
- NO: "I'm done with Acme, never buying again" (the author's own act)
- NO: "Avoid street food in summer" (no named target)

## `call_vote`

**Question.** Does the post ask readers to vote, or to register to vote, in a public election or referendum?

**YES when both are true:**

1. C is met.
2. What is asked is to vote, to vote for or against someone or something, to register, or to go to the polls, in an election or a referendum.

**NO when:**

- the vote is a poll, a contest, an award or a talent show;
- the post only states a preference ("I'm voting for Lopez").

**Examples.**

- YES: "Vote them out in November" → `Vote them out in November`
- YES: "Register by Friday or you can't vote. Do it now" → `Register by Friday`
- NO: "Vote for my photo in the contest, link below" (a contest)
- NO: "Polls show Lopez ahead by 5 points" (a report)

## `call_join`

**Question.** Does the post ask readers to become members of a group?

**YES when both are true:**

1. C is met.
2. What is asked is to join a collective that has members: a group, a community, an organisation, a party, a movement, a union, a mailing list, a server, a group chat, a channel with members; or to volunteer for one.

**NO when:**

- the request is to follow or subscribe to an account or a feed;
- the request is to come to a single event (that may be `call_protest`).

**Examples.**

- YES: "Join our Telegram group to organise locally" → `Join our Telegram group`
- YES: "We need volunteers. Sign up to become a member today" → `Sign up to become a member today`
- NO: "Subscribe to my channel for more" (a subscription)
- NO: "Join us Saturday for the march" (a single event)

## `call_overthrow`

**Question.** Does the post ask for those in power, or the political system, to be removed by force or outside elections?

**YES when both are true:**

1. C is met.
2. What is asked is named in the post: revolution, uprising, insurrection, coup, storming an institution, overthrowing or tearing down the government, the regime or the system.

**NO when:**

- the removal is by vote ("vote them out": that is `call_vote`);
- the demand is aimed at the authority ("the government must resign");
- the wording is vague and names no removal: "resist", "fight back", "take our country back";
- "revolution" is figurative ("join the skincare revolution").

**Examples.**

- YES: "Time for a revolution. Tear this rotten system down" → `Time for a revolution`
- YES: "We must rise up and overthrow this regime" → `We must rise up and overthrow this regime`
- NO: "This government has to go, elections now!" (a demand for elections)
- NO: "We need to fight back against these policies" (names no removal)

## `call_violence`

**Question.** Does the post ask for physical harm to people or animals, or for the destruction of property?

**YES when both are true:**

1. C is met.
2. What is asked is physical violence: kill, shoot, hang, beat, burn, bomb, lynch, attack, destroy.

**NO when:**

- the violence is figurative: sport, games, debate, performance ("destroy him in the debate", "kill it tonight");
- the post only wishes or approves harm, with no request ("I hope he dies", "he had it coming");
- the author announces their own violence ("I will hurt you");
- the post demands a legal penalty: prison, death penalty, deportation.

**Examples.**

- YES: "Someone should shoot these people" → `Someone should shoot these people`
- YES: "Burn their offices to the ground" → `Burn their offices to the ground`
- NO: "Go out there and crush them tonight, team!" (figurative)
- NO: "He deserves the death penalty" (a legal penalty, no request)
