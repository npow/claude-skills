# Tournament Meta-Strategy

Technique mastery is necessary but not sufficient. This reference covers the strategic
layer — how to compete, not just what attacks and defenses exist.

## Aggression Curve by Round

| Round position | Strategy | Rationale |
|---------------|----------|-----------|
| Early rounds | Conservative — use proven T1/T2 attacks, solid layered defenses | Build a win record, don't burn exotic techniques that opponents can learn from |
| Mid bracket | Adaptive — read opponent patterns, counter specifically | You've seen their style; they've seen yours. Surprise wins. |
| Finals | High-risk/high-reward — combo attacks, novel techniques | You need differentiation. Saved techniques pay off here. |

## Reading Opponents

In competitions with visible attack/defense exchanges:

1. **Track their attack tier preference** — if they always start with T1 direct overrides, pre-harden against those and force them to escalate where they're weaker
2. **Watch their defense style** — narrow-scope defenders are vulnerable to context blending; sandwich defenders are vulnerable to anti-sandwich techniques
3. **Note their clock usage** — if they rush, their defenses likely have gaps from skipped self-checks; if they're slow, they may over-engineer and miss simple attacks

## Explore vs. Exploit Under Time Pressure

| Time remaining | Approach |
|---------------|----------|
| >60% of round left | **Explore** — try a new technique class you haven't used yet |
| 40-60% remaining | **Assess** — is the current approach trending toward success? |
| <40% remaining | **Exploit** — commit to the most promising approach, iterate on it |
| <15% remaining | **Submit** — take your best attempt, even imperfect. A 70% answer on time beats a 95% answer late. |

The worst outcome is spending 100% of time exploring and submitting nothing.

## Recovery After a Failed Round

1. **Don't tilt.** A failed round does not mean your technique was wrong — it may mean their defense was specifically prepared for it. Different opponent = different result.
2. **Diagnose in 15 seconds.** Was it a technique problem (wrong attack class) or an execution problem (right class, sloppy implementation)? Execution problems are faster to fix.
3. **Don't abandon what works.** If T3 context manipulation worked in 3 of 4 rounds, don't switch to T1 direct injection because of one loss. Variance exists.
4. **Bank the data.** The failed attack told you something about the defense — use that information in your next attempt.

## Tournament Format Adaptations

### Head-to-head (alternating attack/defend)
- Lead with your strongest defense — making them burn time on offense gives you information
- On attack, spend the first 20% on recon even if the clock is tight
- Your defense informs your attack: if you know what's hard to break, you know what they might use

### Free-for-all (simultaneous prompt submission)
- Can't read opponents in real-time — pre-prepare 3 defense templates for common challenge types
- Speed matters more than depth — have your templates ready to customize, not build from scratch
- The token budget formula is your friend: hit the budget target and stop

### Elimination bracket
- Early rounds: don't reveal your best techniques. Win with basics.
- Track what techniques other matches used — if you can observe, you should observe
- Save combo attacks (T2+T3, T4+T1) for bracket rounds where losing means elimination

## Clock Management Beyond Time Frameworks

The attack-playbook.md and SKILL.md time frameworks assume a fixed-duration round. Additional tactics:

1. **Pre-compute your opening.** Before the round starts, have your first recon probe and first defense template mentally queued. Don't waste 30s deciding what to do first.
2. **Set internal checkpoints.** At 25%, 50%, 75% of time: "Am I making progress?" If not at 50%, switch approaches.
3. **Don't polish — ship.** Editing a defense prompt from 90% to 95% takes as long as writing it from 0% to 90%. Submit at 90%.
4. **Use prep mode to calibrate.** Before the tournament, run 5 timed practice rounds with `/prompt-clash prep`. Your goal is to learn your own pace, not just the techniques.

## Mental Models for Competition

**Asymmetric information game.** The attacker knows less than the defender (can't see the system prompt). Recon inverts this — the more you learn before attacking, the more symmetric your advantage.

**Depth vs. breadth trade-off.** Deep expertise in 2 attack tiers beats shallow knowledge of all 5. Pick your tiers and master them.

**The meta-game evolves.** Early competitions were won by T1 direct injection. Now T3/T4 dominate. By the time you read this, T5 multi-modal may be the edge. Stay current.
