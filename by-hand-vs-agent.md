section 1: both produced spec, implementation, tests, CI, and provenance; the supervised spec has more detail; the agent extracted normalisation into a separate module

section 2: The agent was faster, but it required broad file-write access upfront, which is a trust/safety trade-off you wouldn't accept on a real codebase.

section 3: The agent produced more files faster, but the review burden shifted to you. You can't verify correctness without reading everything it wrote.  The agent's provenance note is shallow compared to the one you extracted manually in K 5.W.7. It skipped model, context loaded, plan deviations, and untested items.

section 4: the normalise_agent.py extraction is a real answer. The agent spotted a refactor opportunity you didn't take in the supervised chain.

section 5: supervised is slower, exhausting as I need to follow every idea AI is checking or implementing. async is unsafe and a lot of work can be lost if ai goes in wrong direction

section 6: provide a bounded task with clear scope and review checkpoints