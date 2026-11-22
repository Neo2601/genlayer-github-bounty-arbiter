# GitHub Bounty Arbiter — GenLayer Intelligent Contract Primitive

A standalone, reusable **GenLayer Intelligent Contract** (`py-genlayer v0.2.17`) that automates open-source GitHub PR bounty escrow and settlement using **Optimistic Democracy** multi-validator consensus.

## Purpose
Traditional smart contracts cannot natively inspect off-chain pull requests or verify qualitative acceptance criteria without centralized oracles. `GitHubBountyArbiter` enables trustless bounty creation where funds are escrowed on-chain and released only after GenLayer validators independently fetch and verify the target GitHub URL against the defined criteria.

## State Design
- **`Bounty` (`@allow_storage` dataclass):** Stores `creator`, `contributor`, `repo_pr_url`, `criteria`, `reward_amount`, `resolved`, and `approved`.
- **`bounties` (`TreeMap[u256, Bounty]`):** Deterministic on-chain registry of bounties.
- **`next_id` (`u256`):** Monotonic counter generating unique bounty IDs.
- All state updates and native transfers occur deterministically **after** non-deterministic consensus resolves.

## Consensus & Equivalence Logic
Inside `evaluate_bounty(bounty_id)`, the contract uses `gl.vm.run_nondet(leader_fn, validator_fn)`:
1. **`leader_fn`:** Renders the live `repo_pr_url` via `gl.nondet.web.render(..., mode="text")`, evaluates fulfillment against `criteria` via `gl.nondet.exec_prompt(...)`, and normalizes the decision strictly to `"APPROVED"` or `"REJECTED"`.
2. **`validator_fn`:** Ensures the leader returned a valid `gl.vm.Return`, independently re-fetches and evaluates the same live URL, and verifies `leader_result.calldata == validator_decision` before finalizing state changes and executing `_Recipient(bounty.contributor).emit_transfer(...)`.

## Deployment & Verification (GenLayer Studio)
- **Contract Address:** `0x4b633e43d706e21856d618444F615A3c6A0FAC5C`
- **Deployment TX Hash:** `0x9d962b61a4428b1aeaa161d89f439e8eab98e1e74594ce6ed90792560acc8c82`
- **Explorer Link:** [View on GenLayer Studio Explorer](https://explorer-studio.genlayer.com/address/0x4b633e43d706e21856d618444F615A3c6A0FAC5C)
- **Consensus Status:** `FINALIZED` (`MAJORITY_AGREE`)

## Contract Interface
- `create_bounty(contributor: str, repo_pr_url: str, criteria: str)` *(payable write)*: Escrows reward funds and registers bounty acceptance criteria.
- `evaluate_bounty(bounty_id: int)` *(write)*: Runs multi-validator web verification and releases funds if `APPROVED`.
- `get_bounty(bounty_id: int) -> str` *(view)*: Returns JSON metadata and resolution status of a bounty.
- `get_total_bounties() -> int` *(view)*: Returns total bounties created.
