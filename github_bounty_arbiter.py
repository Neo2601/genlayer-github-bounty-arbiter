# v0.2.17
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from genlayer import *


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


@allow_storage
@dataclass
class Bounty:
    creator: Address
    contributor: Address
    repo_pr_url: str
    criteria: str
    reward_amount: u256
    resolved: bool
    approved: bool


class GitHubBountyArbiter(gl.Contract):
    bounties: TreeMap[u256, Bounty]
    next_id: u256

    def __init__(self):
        self.next_id = u256(1)

    @gl.public.write.payable
    def create_bounty(self, contributor: str, repo_pr_url: str, criteria: str) -> None:
        if len(repo_pr_url) == 0:
            raise gl.vm.UserError("PR URL required")
        if len(criteria) == 0:
            raise gl.vm.UserError("Criteria required")

        bounty_id = self.next_id
        self.bounties[bounty_id] = Bounty(
            creator=gl.message.sender_address,
            contributor=Address(contributor),
            repo_pr_url=repo_pr_url,
            criteria=criteria,
            reward_amount=gl.message.value,
            resolved=False,
            approved=False,
        )
        self.next_id = u256(bounty_id + 1)

    @gl.public.write
    def evaluate_bounty(self, bounty_id: int) -> None:
        key = u256(bounty_id)
        if key not in self.bounties:
            raise gl.vm.UserError("Bounty not found")

        bounty = self.bounties[key]
        if bounty.resolved:
            raise gl.vm.UserError("Bounty already resolved")

        pr_url = bounty.repo_pr_url
        criteria = bounty.criteria

        def leader_fn() -> str:
            page_text = gl.nondet.web.render(pr_url, mode="text")
            prompt = (
                f"You are a strict code bounty arbiter.\n"
                f"Criteria: {criteria}\n"
                f"Pull Request Content:\n{page_text[:4000]}\n"
                f"Does this PR satisfy the criteria? Reply strictly with APPROVED or REJECTED."
            )
            decision = gl.nondet.exec_prompt(prompt).strip().upper()
            return "APPROVED" if "APPROVED" in decision else "REJECTED"

        def validator_fn(leader_result: gl.vm.Result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            validator_decision = leader_fn()
            return leader_result.calldata == validator_decision

        verdict = gl.vm.run_nondet(leader_fn, validator_fn)
        bounty.resolved = True

        if verdict == "APPROVED":
            bounty.approved = True
            if bounty.reward_amount > u256(0):
                _Recipient(bounty.contributor).emit_transfer(value=bounty.reward_amount)

    @gl.public.view
    def get_bounty(self, bounty_id: int) -> str:
        key = u256(bounty_id)
        if key not in self.bounties:
            raise gl.vm.UserError("Bounty not found")
        b = self.bounties[key]
        return json.dumps({
            "creator": str(b.creator),
            "contributor": str(b.contributor),
            "repo_pr_url": b.repo_pr_url,
            "criteria": b.criteria,
            "reward_amount": str(b.reward_amount),
            "resolved": b.resolved,
            "approved": b.approved,
        })

    @gl.public.view
    def get_total_bounties(self) -> int:
        return int(self.next_id) - 1
