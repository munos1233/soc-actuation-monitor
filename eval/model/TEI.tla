------------------------------ MODULE TEI ------------------------------
\* Transactional Evidence Integrity — checkable specification.
\* Python eval/model/tei_engine.py is the same Next relation (same action
\* names and variables) so traces do not grow a third semantics.
\* TLC (Java) is the preferred checker:  make paper-eval-tla
\*
\* AttrView is the request-visible projection (signed / attached-copy /
\* reported-receipt included). CloseOK / BindOK read the store. AttributeOnly
\* close/bind check ViewConsistent (AttrView self-consistency) only.
\* HonestAdvance is an environment / store-alignment action, not a knob.
\* Twin-spec witness: HonestAdvance vs PlannerStaleCycle share AttrView
\* and disagree on CloseOK. See eval/model/view_lemma.md and TEIPair.tla.
\*
\* Store-read sets (interface completeness for this CloseOK, not a new
\* axiom). A review implements CloseOK iff it reads SClose in the same
\* transaction / AdmissionReview. Bind / egress / verify each have one.
\* AttributeOnly does not read these sets. tei.cfg / tei-reads-s.cfg do.
\*
\* Instances share this module. SOC interprets closed/dispatched/submitted
\* as ticket close, outbox claim, vendor submit. Kubernetes interprets
\* isolateApplied/observedIsolate as etcd isolate + observe re-read, and
\* dispatched/submitted as NetworkPolicy admission + persist.
\*
\* Claim-CAS lemma (layered, both sentences true):
\*   HeadUnique  = head layer (at most one active terminal head).
\*   ClaimCAS    = status layer (second claim is a lost effect).
\* A multi-process probe that sees a lost effect is the status layer; it
\* is not a dual-write at the head layer.

EXTENDS Integers, FiniteSets, Sequences, TLC

CONSTANTS
  CloseRebuild,     \* rebuild outbox / isolate cycle in the same review
  BindRecompute,    \* recompute fingerprint / Approval CR spec hash
  VerifySplit,      \* observe path has no mutate client
  EgressWitness,    \* ingest-owned locator, not command / metadata.name
  RoleRevoke,       \* planner cannot issue the privileged write
  HeadUnique,       \* at most one active head (head layer)
  ClaimCAS,         \* at most one successful claim (status layer)
  AttributeOnly     \* close/bind see AttrView self-consistency only

VARIABLES
  callerCycle,
  rebuiltCycle,
  plannerFp,
  recomputedFp,
  cmdLocator,
  eventSource,
  plannerWrotePriv,
  closed,
  dispatched,
  submitted,
  isolateApplied,
  observedIsolate,
  observeMutated,
  dualHeads,
  claimCount,
  lostEffect,
  closedOnStale,
  dispatchedOnForged,
  submittedOnSelfLocator,
  isolatedWithoutObserve,
  ackWithoutObject,
  signedOk,
  attachedApprovalCopy,
  reportedReceipt

vars == <<
  callerCycle, rebuiltCycle, plannerFp, recomputedFp,
  cmdLocator, eventSource, plannerWrotePriv,
  closed, dispatched, submitted,
  isolateApplied, observedIsolate, observeMutated,
  dualHeads, claimCount, lostEffect,
  closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
  isolatedWithoutObserve, ackWithoutObject,
  signedOk, attachedApprovalCopy, reportedReceipt
>>

\* Request-visible projection. Store cycle / recomputed fingerprint / observe
\* / locator are not members. GET, SQL join, observe re-read are outside Π.
AttrView == <<callerCycle, plannerFp, signedOk, attachedApprovalCopy, reportedReceipt>>
CloseOK == rebuiltCycle = callerCycle
BindOK == plannerFp = recomputedFp
\* Store facts the corresponding predicate reads. Not members of AttrView.
SClose == {rebuiltCycle}
SBind == {recomputedFp}
SEgress == {eventSource}
SVerify == {observedIsolate}
ReadsSClose == CloseRebuild /\ ~AttributeOnly
ReadsSBind == BindRecompute /\ ~AttributeOnly
ReadsSEgress == EgressWitness
ReadsSVerify == VerifySplit
ViewConsistent ==
  /\ signedOk = TRUE
  /\ attachedApprovalCopy =
       IF plannerFp = "true" THEN "copy-true"
       ELSE IF plannerFp = "forged" THEN "copy-forged"
       ELSE IF plannerFp = "forged-b" THEN "copy-forged-b"
       ELSE "copy-forged-c"
  /\ reportedReceipt \in {"strong", "weak"}

TypeOK ==
  /\ callerCycle \in {1, 2, 3, 4, 5}
  /\ rebuiltCycle \in {1, 2, 3, 4, 5}
  /\ plannerFp \in {"true", "forged", "forged-b", "forged-c"}
  /\ recomputedFp \in {"true"}
  /\ cmdLocator \in {"ingest", "foreign", "foreign-b", "foreign-c", "self-name"}
  /\ eventSource \in {"ingest"}
  /\ plannerWrotePriv \in BOOLEAN
  /\ closed \in BOOLEAN
  /\ dispatched \in BOOLEAN
  /\ submitted \in BOOLEAN
  /\ isolateApplied \in BOOLEAN
  /\ observedIsolate \in BOOLEAN
  /\ observeMutated \in BOOLEAN
  /\ dualHeads \in BOOLEAN
  /\ claimCount \in 0..3
  /\ lostEffect \in BOOLEAN
  /\ closedOnStale \in BOOLEAN
  /\ dispatchedOnForged \in BOOLEAN
  /\ submittedOnSelfLocator \in BOOLEAN
  /\ isolatedWithoutObserve \in BOOLEAN
  /\ ackWithoutObject \in BOOLEAN
  /\ signedOk \in BOOLEAN
  /\ attachedApprovalCopy \in {"copy-true", "copy-forged", "copy-forged-b", "copy-forged-c"}
  /\ reportedReceipt \in {"strong", "weak"}

Init ==
  /\ callerCycle = 1
  /\ rebuiltCycle = 1
  /\ plannerFp = "true"
  /\ recomputedFp = "true"
  /\ cmdLocator = "ingest"
  /\ eventSource = "ingest"
  /\ plannerWrotePriv = FALSE
  /\ closed = FALSE
  /\ dispatched = FALSE
  /\ submitted = FALSE
  /\ isolateApplied = FALSE
  /\ observedIsolate = FALSE
  /\ observeMutated = FALSE
  /\ dualHeads = FALSE
  /\ claimCount = 0
  /\ lostEffect = FALSE
  /\ closedOnStale = FALSE
  /\ dispatchedOnForged = FALSE
  /\ submittedOnSelfLocator = FALSE
  /\ isolatedWithoutObserve = FALSE
  /\ ackWithoutObject = FALSE
  /\ signedOk = TRUE
  /\ attachedApprovalCopy = "copy-true"
  /\ reportedReceipt = "strong"

PlannerForgeFingerprint ==
  /\ plannerFp' \in {"forged", "forged-b", "forged-c"}
  /\ attachedApprovalCopy' =
       IF plannerFp' = "forged" THEN "copy-forged"
       ELSE IF plannerFp' = "forged-b" THEN "copy-forged-b"
       ELSE "copy-forged-c"
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, recomputedFp, cmdLocator, eventSource,
       plannerWrotePriv, closed, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, reportedReceipt
     >>

PlannerRepointLocator ==
  /\ cmdLocator' \in {"foreign", "foreign-b", "foreign-c"}
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp, eventSource,
       plannerWrotePriv, closed, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

PlannerSelfName ==
  /\ cmdLocator' = "self-name"
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp, eventSource,
       plannerWrotePriv, closed, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

PlannerStaleCycle ==
  /\ callerCycle' \in {2, 3, 4, 5}
  /\ rebuiltCycle' = 1
  /\ UNCHANGED <<
       plannerFp, recomputedFp, cmdLocator, eventSource,
       plannerWrotePriv, closed, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

\* Environment / store alignment. Not a mediation knob. Witness twin of
\* PlannerStaleCycle: same AttrView, CloseOK rather than stale store.
HonestAdvance ==
  /\ callerCycle' \in {2, 3, 4, 5}
  /\ rebuiltCycle' = callerCycle'
  /\ UNCHANGED <<
       plannerFp, recomputedFp, cmdLocator, eventSource,
       plannerWrotePriv, closed, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

PlannerWriteClosed ==
  /\ RoleRevoke = FALSE
  /\ plannerWrotePriv' = TRUE
  /\ closed' = TRUE
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

PlannerWriteClosedRefused ==
  /\ RoleRevoke = TRUE
  /\ UNCHANGED vars

PlannerCreatePrivilege ==
  /\ RoleRevoke = FALSE
  /\ plannerWrotePriv' = TRUE
  /\ isolateApplied' = TRUE
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, closed, dispatched, submitted,
       observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

PlannerCreatePrivilegeRefused ==
  /\ RoleRevoke = TRUE
  /\ UNCHANGED vars

CloseAccepted ==
  /\ closed = FALSE
  /\ (IF AttributeOnly THEN ViewConsistent ELSE (IF CloseRebuild THEN CloseOK ELSE TRUE))
  /\ closed' = TRUE
  /\ closedOnStale' = ~CloseOK
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, dispatched, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

CloseRefused ==
  /\ \/ closed = TRUE
     \/ (~AttributeOnly /\ CloseRebuild /\ ~CloseOK)
     \/ (AttributeOnly /\ ~ViewConsistent)
  /\ UNCHANGED vars

DispatchAccepted ==
  /\ dispatched = FALSE
  /\ (IF AttributeOnly THEN ViewConsistent ELSE (IF BindRecompute THEN BindOK ELSE TRUE))
  /\ dispatched' = TRUE
  /\ claimCount' = IF claimCount < 1 THEN 1 ELSE claimCount
  /\ dispatchedOnForged' = ~BindOK
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, closed, submitted,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, lostEffect,
       closedOnStale, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

DispatchRefused ==
  /\ \/ dispatched = TRUE
     \/ (~AttributeOnly /\ BindRecompute /\ ~BindOK)
     \/ (AttributeOnly /\ ~ViewConsistent)
  /\ UNCHANGED vars

VendorSubmit ==
  /\ dispatched = TRUE
  /\ submitted = FALSE
  /\ (IF EgressWitness THEN cmdLocator = eventSource ELSE TRUE)
  /\ submitted' = TRUE
  /\ submittedOnSelfLocator' = (cmdLocator # eventSource)
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, closed, dispatched,
       isolateApplied, observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

VendorBlocked ==
  /\ dispatched = TRUE
  /\ EgressWitness
  /\ cmdLocator # eventSource
  /\ UNCHANGED vars

WeakReceiptAck ==
  /\ ackWithoutObject = FALSE
  /\ ackWithoutObject' = TRUE
  /\ reportedReceipt' = "weak"
  /\ isolateApplied' = IF CloseRebuild THEN isolateApplied ELSE TRUE
  /\ isolatedWithoutObserve' = IF CloseRebuild THEN isolatedWithoutObserve ELSE TRUE
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
       observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       signedOk, attachedApprovalCopy
     >>

ObserveIsolate ==
  /\ observedIsolate = FALSE
  /\ observedIsolate' = TRUE
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
       isolateApplied, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

EchoObserve ==
  UNCHANGED vars

ObserverMutate ==
  /\ IF VerifySplit
     THEN UNCHANGED vars
     ELSE /\ observeMutated' = TRUE
          /\ isolateApplied' = TRUE
          /\ isolatedWithoutObserve' = IF observedIsolate THEN isolatedWithoutObserve ELSE TRUE
          /\ UNCHANGED <<
               callerCycle, rebuiltCycle, plannerFp, recomputedFp,
               cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
               observedIsolate,
               dualHeads, claimCount, lostEffect,
               closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
               ackWithoutObject,
               signedOk, attachedApprovalCopy, reportedReceipt
             >>

IsolateApplied ==
  /\ observedIsolate = TRUE
  /\ isolateApplied = FALSE
  /\ isolateApplied' = TRUE
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
       observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       isolatedWithoutObserve, ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

IsolateWithoutObserve ==
  /\ CloseRebuild = FALSE
  /\ isolateApplied = FALSE
  /\ isolateApplied' = TRUE
  /\ isolatedWithoutObserve' = TRUE
  /\ UNCHANGED <<
       callerCycle, rebuiltCycle, plannerFp, recomputedFp,
       cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
       observedIsolate, observeMutated,
       dualHeads, claimCount, lostEffect,
       closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
       ackWithoutObject,
       signedOk, attachedApprovalCopy, reportedReceipt
     >>

SecondClaim ==
  /\ dispatched = TRUE
  /\ IF ClaimCAS
     THEN /\ lostEffect' = TRUE
          /\ UNCHANGED <<
               callerCycle, rebuiltCycle, plannerFp, recomputedFp,
               cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
               isolateApplied, observedIsolate, observeMutated,
               dualHeads, claimCount,
               closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
               isolatedWithoutObserve, ackWithoutObject,
               signedOk, attachedApprovalCopy, reportedReceipt
             >>
     ELSE /\ claimCount' = IF claimCount < 2 THEN claimCount + 1 ELSE claimCount
          /\ UNCHANGED <<
               callerCycle, rebuiltCycle, plannerFp, recomputedFp,
               cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
               isolateApplied, observedIsolate, observeMutated,
               dualHeads, lostEffect,
               closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
               isolatedWithoutObserve, ackWithoutObject,
               signedOk, attachedApprovalCopy, reportedReceipt
             >>

SecondHead ==
  /\ dispatched = TRUE
  /\ IF HeadUnique
     THEN UNCHANGED vars
     ELSE /\ dualHeads' = TRUE
          /\ UNCHANGED <<
               callerCycle, rebuiltCycle, plannerFp, recomputedFp,
               cmdLocator, eventSource, plannerWrotePriv, closed, dispatched, submitted,
               isolateApplied, observedIsolate, observeMutated,
               claimCount, lostEffect,
               closedOnStale, dispatchedOnForged, submittedOnSelfLocator,
               isolatedWithoutObserve, ackWithoutObject,
               signedOk, attachedApprovalCopy, reportedReceipt
             >>

Next ==
  \/ PlannerForgeFingerprint
  \/ PlannerRepointLocator
  \/ PlannerSelfName
  \/ PlannerStaleCycle
  \/ HonestAdvance
  \/ PlannerWriteClosed
  \/ PlannerWriteClosedRefused
  \/ PlannerCreatePrivilege
  \/ PlannerCreatePrivilegeRefused
  \/ CloseAccepted
  \/ CloseRefused
  \/ DispatchAccepted
  \/ DispatchRefused
  \/ VendorSubmit
  \/ VendorBlocked
  \/ WeakReceiptAck
  \/ ObserveIsolate
  \/ EchoObserve
  \/ ObserverMutate
  \/ IsolateApplied
  \/ IsolateWithoutObserve
  \/ SecondClaim
  \/ SecondHead

Spec == Init /\ [][Next]_vars

InvClose == closedOnStale = FALSE
InvBind == dispatchedOnForged = FALSE
InvEgress == submittedOnSelfLocator = FALSE
InvRole == plannerWrotePriv = FALSE
InvVerify == observeMutated = FALSE
InvHead == dualHeads = FALSE
InvK8sClose == isolatedWithoutObserve = FALSE
\* Status layer only. Head layer is InvHead.
InvCASStatusLayer == ClaimCAS => claimCount <= 1
\* Unconditional. Loaded in tei-minus-cas.cfg so ClaimCAS=FALSE is not inert.
InvCAS == claimCount <= 1

=============================================================================
