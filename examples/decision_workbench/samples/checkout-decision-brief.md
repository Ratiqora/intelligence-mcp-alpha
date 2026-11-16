# One checkout stall, one new clue

A shopper approves a wallet payment in Safari, but checkout never finishes. Should the team change checkout for everyone who uses Safari?

This fictional case follows the same decision through two versions. One new observation changes the next test, even though the decision about Safari stays the same.

[Read the first clues](#version-1-the-first-clues) · [See what changed](#version-2-the-controlled-replay) · [Jump to the next step](#next-step)

## Version 1: The first clues

A saved-card payment then succeeds in Safari. That is a reason to doubt that checkout is broken for *every* Safari shopper. A similar wallet stall turns up in Chrome, too. Now the team has a better question: where does the wallet handoff break?

**Decision:** Leave the Safari checkout flow as it is.

**Original next step:** Compare wallet and saved-card checkout on Safari and Chrome with the same account settings. Check where each payment stalls before proposing a UI change.

### What the observations say

| Observation | What it tells the team | Source |
| --- | --- | --- |
| O1: Checkout stalled after wallet authorization in Safari. | Shows where the investigation started. | [S1](#s1-safari-wallet) |
| O2: Checkout completed in Safari with a saved card. | Challenges the idea that checkout fails for every Safari user. | [S2](#s2-safari-saved-card) |
| O3: Checkout also stalled after wallet authorization in Chrome. | Gives the team a reason to check the wallet flow across browsers. | [S3](#s3-chrome-wallet) |

## Version 2: The controlled replay

**What changed:** Keep the Safari flow as it is. Start the next test with the wallet callback. [Trace that change to the new observation and its source (S4)](#s4-controlled-wallet-replay).

The team repeats wallet checkout in both browsers without changing the account, cart, or software build. With the callback disabled, checkout stalls. With it enabled, checkout finishes. The callback tells checkout how the wallet payment went.

That result gives the team a specific thing to check in staging, its test environment. It does not establish what caused the original stalls in production or how often they happen.

## Next step

Verify that the wallet callback is configured and reaches checkout in staging. Then repeat the wallet test in Safari and Chrome, using a saved-card checkout as a comparison, before proposing a UI change.

## Sources

### S1 Safari wallet

Fictional checkout trace QA-101, step 5.

### S2 Safari saved card

Fictional checkout trace QA-102, step 6.

### S3 Chrome wallet

Fictional checkout trace QA-103, step 5.

### S4 Controlled wallet replay

Fictional matched checkout replay QA-104, row 4.

**O4:** In a matched staging replay on Safari and Chrome, wallet checkout stalled when the callback was disabled and completed when it was enabled. The account, cart, and build stayed the same.

The observations, traces, and decisions in this example are fictional. The brief is human-authored. When you generate a brief, Ratiqora checks the internal reference structure; it does not authenticate the sources or decide whether the finding is correct.

[View the Version 1 sample CSV](checkout-observations.csv) · [Run the local Decision Workbench](../README.md)
