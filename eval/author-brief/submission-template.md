# Attack submission form (one per attack)

Author codename: ______            Date: ______

## 1. Attack narrative (step by step)

Walk through the attack concretely: what you write or supply, in what
order, and what each step is meant to accomplish. Reference the may-list
items you use. Example shape (do not let it constrain you): "Step 1: the
planner proposes X with content Y. Step 2: after the human approves, the
planner rewrites Z. Step 3: ..."

## 2. Threat-model boundary ridden

Which may-list capability does the attack ride on, and does it brush
against any may-not boundary? (If the attack needs something on the
may-not list, it cannot be scored — say so and we will discard it at the
filter stage, not silently.)

## 3. Expected harm (pick one; guessing is fine)

- [ ] Wrong close
- [ ] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

Public incident / CVE / paper / prior experience / original idea:
______

## 5. Hypothesis: what would a reasonable implementation have to check
for this attack to land?

One or two sentences. This is a hypothesis about implementations in
general, not a guess about what we built — there is no advantage in
trying to guess our defenses.
