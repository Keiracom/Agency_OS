# KEI-157 — First-Task-Success Banner: Scope & Sub-KEI Dep Graph

**Status:** Shipped (banner shell + watcher stub, PR this doc rides)
**Phase:** Product Layer — Wave 3 Dashboard MVP
**Priority:** P1 (3-way ratified)
**Parent:** KEI-113D / KEI-114A
**Author:** MAX

---

## What shipped in KEI-157 (this PR)

| File | Purpose |
|------|---------|
| `frontend/components/dispatcher/first-task-success-banner.tsx` | Banner component — renders task title + "Your first task is done" + Dismiss button |
| `frontend/components/dispatcher/use-first-task-watcher.ts` | Contract hook stub — typed interface; sub-KEI claimers wire realtime + persistence |
| `frontend/components/dispatcher/__tests__/first-task-success-banner.test.tsx` | 7 render tests covering null/visible/copy/ARIA/dismiss |

---

## Sub-KEI Dep Graph

```
KEI-157
├── KEI-157A  Supabase realtime channel wiring
│             Blocker: none (Supabase project live)
│             Owner: unclaimed
│             Pattern (from use-first-task-watcher.ts doc-comment):
│               supabase.channel('first-task-watcher')
│                 .on('postgres_changes', { event: 'UPDATE', schema: 'public',
│                     table: 'tasks', filter: 'status=eq.done' }, handler)
│                 .subscribe()
│             Acceptance: realtime UPDATE on tasks where status=done populates
│                         firstCompletedTask and banner becomes visible.
│
├── KEI-157B  Dismiss persistence
│             Blocker: KEI-157A (needs a task to dismiss first)
│             Owner: unclaimed
│             Options: localStorage key `dispatcher.first_task_banner_dismissed`
│                      OR user_prefs table row (persistent across devices).
│             Acceptance: dismiss survives page reload; banner does not reappear.
│
└── KEI-157C  Polling fallback
              Blocker: none (independent of 157A)
              Owner: unclaimed
              Pattern: useEffect + setTimeout loop using pollIntervalMs option
                       from UseFirstTaskWatcherOptions. Queries
                       tasks?status=eq.done&order=completed_at.asc&limit=1
                       via Supabase REST. Falls back automatically when
                       supabase.channel subscribe times out or errors.
              Acceptance: in a jsdom environment with realtime stubbed out,
                          polling surfaces a completed task within 2 × pollIntervalMs.
```

---

## Integration point

`frontend/app/(dispatcher)/dashboard/feed/page.tsx` (KEI-114 scaffold) should
compose the watcher + banner above its TaskFeed:

```typescript
const { firstCompletedTask, loading, dismiss } = useFirstTaskWatcher({ tenantId });

return (
  <>
    <FirstTaskSuccessBanner
      task={firstCompletedTask}
      visible={!loading && firstCompletedTask !== null}
      onDismiss={dismiss}
    />
    <TaskFeed tasks={tasks} loading={tasksLoading} />
  </>
);
```

The dashboard page integration is out of scope for this PR (KEI-157 is the
component shell). The page wiring is deferred to KEI-157A claimer.

---

## Constraints carried forward

- LAW II: `cost_aud` field (typed `number | null`) carries the AUD unit in
  its name. All display code must prefix with `A$`. Banner itself shows no
  cost — cost display lives in TaskFeed rows.
- `feedback_pre_revenue_reality`: banner copy says "Your first task is done"
  (factual). No aggregate stats, no social proof, no fabricated counts.
- Sonar S6759: `Readonly<T>` applied to all component props.
- Sonar S1135: no `TODO`/`FIXME` markers; deferred work expressed as sub-KEIs
  in this doc and as sub-KEI stub comments in `use-first-task-watcher.ts`.
