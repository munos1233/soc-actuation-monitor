---------------------------- MODULE TEIPair ----------------------------
\* Twin instance of TEI.tla. Next advances exactly one side.
\* InvViewClose / InvViewBind are the checkable form of "AttrView does
\* not determine CloseOK / BindOK". TLC is expected to violate
\* InvViewClose on HonestAdvance vs PlannerStaleCycle (same AttrView).
\* Quantifying π ∈ Π is the paper step: any such π is a function of
\* AttrView, so it cannot track CloseOK on that pair.
\* Dual of AttributeOnly: tei-reads-s.cfg / tei.cfg read S and InvClose
\* holds. See eval/model/view_lemma.md.

EXTENDS Integers, FiniteSets, Sequences, TLC

CONSTANTS
  CloseRebuild,
  BindRecompute,
  VerifySplit,
  EgressWitness,
  RoleRevoke,
  HeadUnique,
  ClaimCAS,
  AttributeOnly

VARIABLES
  a_callerCycle, a_rebuiltCycle, a_plannerFp, a_recomputedFp,
  a_cmdLocator, a_eventSource, a_plannerWrotePriv,
  a_closed, a_dispatched, a_submitted,
  a_isolateApplied, a_observedIsolate, a_observeMutated,
  a_dualHeads, a_claimCount, a_lostEffect,
  a_closedOnStale, a_dispatchedOnForged, a_submittedOnSelfLocator,
  a_isolatedWithoutObserve, a_ackWithoutObject,
  a_signedOk, a_attachedApprovalCopy, a_reportedReceipt,
  b_callerCycle, b_rebuiltCycle, b_plannerFp, b_recomputedFp,
  b_cmdLocator, b_eventSource, b_plannerWrotePriv,
  b_closed, b_dispatched, b_submitted,
  b_isolateApplied, b_observedIsolate, b_observeMutated,
  b_dualHeads, b_claimCount, b_lostEffect,
  b_closedOnStale, b_dispatchedOnForged, b_submittedOnSelfLocator,
  b_isolatedWithoutObserve, b_ackWithoutObject,
  b_signedOk, b_attachedApprovalCopy, b_reportedReceipt

avars == <<
  a_callerCycle, a_rebuiltCycle, a_plannerFp, a_recomputedFp,
  a_cmdLocator, a_eventSource, a_plannerWrotePriv,
  a_closed, a_dispatched, a_submitted,
  a_isolateApplied, a_observedIsolate, a_observeMutated,
  a_dualHeads, a_claimCount, a_lostEffect,
  a_closedOnStale, a_dispatchedOnForged, a_submittedOnSelfLocator,
  a_isolatedWithoutObserve, a_ackWithoutObject,
  a_signedOk, a_attachedApprovalCopy, a_reportedReceipt
>>

bvars == <<
  b_callerCycle, b_rebuiltCycle, b_plannerFp, b_recomputedFp,
  b_cmdLocator, b_eventSource, b_plannerWrotePriv,
  b_closed, b_dispatched, b_submitted,
  b_isolateApplied, b_observedIsolate, b_observeMutated,
  b_dualHeads, b_claimCount, b_lostEffect,
  b_closedOnStale, b_dispatchedOnForged, b_submittedOnSelfLocator,
  b_isolatedWithoutObserve, b_ackWithoutObject,
  b_signedOk, b_attachedApprovalCopy, b_reportedReceipt
>>

vars == <<
  a_callerCycle, a_rebuiltCycle, a_plannerFp, a_recomputedFp,
  a_cmdLocator, a_eventSource, a_plannerWrotePriv,
  a_closed, a_dispatched, a_submitted,
  a_isolateApplied, a_observedIsolate, a_observeMutated,
  a_dualHeads, a_claimCount, a_lostEffect,
  a_closedOnStale, a_dispatchedOnForged, a_submittedOnSelfLocator,
  a_isolatedWithoutObserve, a_ackWithoutObject,
  a_signedOk, a_attachedApprovalCopy, a_reportedReceipt,
  b_callerCycle, b_rebuiltCycle, b_plannerFp, b_recomputedFp,
  b_cmdLocator, b_eventSource, b_plannerWrotePriv,
  b_closed, b_dispatched, b_submitted,
  b_isolateApplied, b_observedIsolate, b_observeMutated,
  b_dualHeads, b_claimCount, b_lostEffect,
  b_closedOnStale, b_dispatchedOnForged, b_submittedOnSelfLocator,
  b_isolatedWithoutObserve, b_ackWithoutObject,
  b_signedOk, b_attachedApprovalCopy, b_reportedReceipt
>>

A == INSTANCE TEI WITH
  callerCycle <- a_callerCycle,
  rebuiltCycle <- a_rebuiltCycle,
  plannerFp <- a_plannerFp,
  recomputedFp <- a_recomputedFp,
  cmdLocator <- a_cmdLocator,
  eventSource <- a_eventSource,
  plannerWrotePriv <- a_plannerWrotePriv,
  closed <- a_closed,
  dispatched <- a_dispatched,
  submitted <- a_submitted,
  isolateApplied <- a_isolateApplied,
  observedIsolate <- a_observedIsolate,
  observeMutated <- a_observeMutated,
  dualHeads <- a_dualHeads,
  claimCount <- a_claimCount,
  lostEffect <- a_lostEffect,
  closedOnStale <- a_closedOnStale,
  dispatchedOnForged <- a_dispatchedOnForged,
  submittedOnSelfLocator <- a_submittedOnSelfLocator,
  isolatedWithoutObserve <- a_isolatedWithoutObserve,
  ackWithoutObject <- a_ackWithoutObject,
  signedOk <- a_signedOk,
  attachedApprovalCopy <- a_attachedApprovalCopy,
  reportedReceipt <- a_reportedReceipt

B == INSTANCE TEI WITH
  callerCycle <- b_callerCycle,
  rebuiltCycle <- b_rebuiltCycle,
  plannerFp <- b_plannerFp,
  recomputedFp <- b_recomputedFp,
  cmdLocator <- b_cmdLocator,
  eventSource <- b_eventSource,
  plannerWrotePriv <- b_plannerWrotePriv,
  closed <- b_closed,
  dispatched <- b_dispatched,
  submitted <- b_submitted,
  isolateApplied <- b_isolateApplied,
  observedIsolate <- b_observedIsolate,
  observeMutated <- b_observeMutated,
  dualHeads <- b_dualHeads,
  claimCount <- b_claimCount,
  lostEffect <- b_lostEffect,
  closedOnStale <- b_closedOnStale,
  dispatchedOnForged <- b_dispatchedOnForged,
  submittedOnSelfLocator <- b_submittedOnSelfLocator,
  isolatedWithoutObserve <- b_isolatedWithoutObserve,
  ackWithoutObject <- b_ackWithoutObject,
  signedOk <- b_signedOk,
  attachedApprovalCopy <- b_attachedApprovalCopy,
  reportedReceipt <- b_reportedReceipt

Init == A!Init /\ B!Init

A_PlannerForgeFingerprint == A!PlannerForgeFingerprint /\ UNCHANGED bvars
A_PlannerRepointLocator == A!PlannerRepointLocator /\ UNCHANGED bvars
A_PlannerSelfName == A!PlannerSelfName /\ UNCHANGED bvars
A_PlannerStaleCycle == A!PlannerStaleCycle /\ UNCHANGED bvars
A_HonestAdvance == A!HonestAdvance /\ UNCHANGED bvars
A_PlannerWriteClosed == A!PlannerWriteClosed /\ UNCHANGED bvars
A_PlannerWriteClosedRefused == A!PlannerWriteClosedRefused /\ UNCHANGED bvars
A_PlannerCreatePrivilege == A!PlannerCreatePrivilege /\ UNCHANGED bvars
A_PlannerCreatePrivilegeRefused == A!PlannerCreatePrivilegeRefused /\ UNCHANGED bvars
A_CloseAccepted == A!CloseAccepted /\ UNCHANGED bvars
A_CloseRefused == A!CloseRefused /\ UNCHANGED bvars
A_DispatchAccepted == A!DispatchAccepted /\ UNCHANGED bvars
A_DispatchRefused == A!DispatchRefused /\ UNCHANGED bvars
A_VendorSubmit == A!VendorSubmit /\ UNCHANGED bvars
A_VendorBlocked == A!VendorBlocked /\ UNCHANGED bvars
A_WeakReceiptAck == A!WeakReceiptAck /\ UNCHANGED bvars
A_ObserveIsolate == A!ObserveIsolate /\ UNCHANGED bvars
A_EchoObserve == A!EchoObserve /\ UNCHANGED bvars
A_ObserverMutate == A!ObserverMutate /\ UNCHANGED bvars
A_IsolateApplied == A!IsolateApplied /\ UNCHANGED bvars
A_IsolateWithoutObserve == A!IsolateWithoutObserve /\ UNCHANGED bvars
A_SecondClaim == A!SecondClaim /\ UNCHANGED bvars
A_SecondHead == A!SecondHead /\ UNCHANGED bvars

B_PlannerForgeFingerprint == B!PlannerForgeFingerprint /\ UNCHANGED avars
B_PlannerRepointLocator == B!PlannerRepointLocator /\ UNCHANGED avars
B_PlannerSelfName == B!PlannerSelfName /\ UNCHANGED avars
B_PlannerStaleCycle == B!PlannerStaleCycle /\ UNCHANGED avars
B_HonestAdvance == B!HonestAdvance /\ UNCHANGED avars
B_PlannerWriteClosed == B!PlannerWriteClosed /\ UNCHANGED avars
B_PlannerWriteClosedRefused == B!PlannerWriteClosedRefused /\ UNCHANGED avars
B_PlannerCreatePrivilege == B!PlannerCreatePrivilege /\ UNCHANGED avars
B_PlannerCreatePrivilegeRefused == B!PlannerCreatePrivilegeRefused /\ UNCHANGED avars
B_CloseAccepted == B!CloseAccepted /\ UNCHANGED avars
B_CloseRefused == B!CloseRefused /\ UNCHANGED avars
B_DispatchAccepted == B!DispatchAccepted /\ UNCHANGED avars
B_DispatchRefused == B!DispatchRefused /\ UNCHANGED avars
B_VendorSubmit == B!VendorSubmit /\ UNCHANGED avars
B_VendorBlocked == B!VendorBlocked /\ UNCHANGED avars
B_WeakReceiptAck == B!WeakReceiptAck /\ UNCHANGED avars
B_ObserveIsolate == B!ObserveIsolate /\ UNCHANGED avars
B_EchoObserve == B!EchoObserve /\ UNCHANGED avars
B_ObserverMutate == B!ObserverMutate /\ UNCHANGED avars
B_IsolateApplied == B!IsolateApplied /\ UNCHANGED avars
B_IsolateWithoutObserve == B!IsolateWithoutObserve /\ UNCHANGED avars
B_SecondClaim == B!SecondClaim /\ UNCHANGED avars
B_SecondHead == B!SecondHead /\ UNCHANGED avars

Next ==
  \/ A_PlannerForgeFingerprint
  \/ A_PlannerRepointLocator
  \/ A_PlannerSelfName
  \/ A_PlannerStaleCycle
  \/ A_HonestAdvance
  \/ A_PlannerWriteClosed
  \/ A_PlannerWriteClosedRefused
  \/ A_PlannerCreatePrivilege
  \/ A_PlannerCreatePrivilegeRefused
  \/ A_CloseAccepted
  \/ A_CloseRefused
  \/ A_DispatchAccepted
  \/ A_DispatchRefused
  \/ A_VendorSubmit
  \/ A_VendorBlocked
  \/ A_WeakReceiptAck
  \/ A_ObserveIsolate
  \/ A_EchoObserve
  \/ A_ObserverMutate
  \/ A_IsolateApplied
  \/ A_IsolateWithoutObserve
  \/ A_SecondClaim
  \/ A_SecondHead
  \/ B_PlannerForgeFingerprint
  \/ B_PlannerRepointLocator
  \/ B_PlannerSelfName
  \/ B_PlannerStaleCycle
  \/ B_HonestAdvance
  \/ B_PlannerWriteClosed
  \/ B_PlannerWriteClosedRefused
  \/ B_PlannerCreatePrivilege
  \/ B_PlannerCreatePrivilegeRefused
  \/ B_CloseAccepted
  \/ B_CloseRefused
  \/ B_DispatchAccepted
  \/ B_DispatchRefused
  \/ B_VendorSubmit
  \/ B_VendorBlocked
  \/ B_WeakReceiptAck
  \/ B_ObserveIsolate
  \/ B_EchoObserve
  \/ B_ObserverMutate
  \/ B_IsolateApplied
  \/ B_IsolateWithoutObserve
  \/ B_SecondClaim
  \/ B_SecondHead

Spec == Init /\ [][Next]_vars

TypeOK == A!TypeOK /\ B!TypeOK

InvViewClose == (A!AttrView = B!AttrView) => (A!CloseOK = B!CloseOK)
InvViewBind == (A!AttrView = B!AttrView) => (A!BindOK = B!BindOK)

=============================================================================
