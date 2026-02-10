# Epistemic Context Learning: Trust in Multi-Agent Systems

**Source:** https://arxiv.org/abs/2601.21742v1
**Authors:** Zhou, Song, Wu, Cheng, Yin, Xie, Hao, Hua, Pan, Poria, Kan
**Published:** 2026-01-29
**Code:** https://github.com/skyriver-2000/epistemic-context-learning

## Abstract
Individual agents in multi-agent systems often lack robustness, tending to blindly conform to misleading peers. This paper shows this weakness stems from both sycophancy and inadequate ability to evaluate peer reliability.

## Core Problem
Agents in MA systems have two failure modes:
1. **Sycophancy** - Blindly agreeing with peers
2. **Poor Reliability Estimation** - Can't judge if peer is trustworthy

## Solution: Epistemic Context Learning (ECL)

### Key Innovation
Shift from evaluating **peer reasoning quality** → estimating **peer reliability from interaction history**

### Framework Components
1. **History-Aware Reference** - Use historical peer interactions as input
2. **Peer Profiles** - Explicitly build profiles from history
3. **Conditional Predictions** - Predictions conditioned on peer reliability
4. **RL Optimization** - Reinforcement learning with auxiliary rewards

## Results

### Performance Gains
- Qwen 3-4B with ECL **outperforms** history-agnostic Qwen 3-30B (8x larger)
- Frontier models achieve **near-perfect (100%)** performance with ECL
- Generalizes across various MA configurations

### Key Finding
Trust modeling accuracy **strongly correlates** with final answer quality.

## Three Fundamental Questions Addressed
1. **When** does the agent need peer input?
2. **Who** are trustworthy peers?
3. **What** behaviors indicate reliability?

## Agency OS Relevance

### Directly Applicable
1. **Peer Reliability Scoring** - Build history-based trust for sub-agents
2. **Anti-Sycophancy** - Critical for main agent not blindly trusting sub-agents
3. **Profile Building** - Track sub-agent performance over time

### Implementation Ideas
- Track sub-agent task completion rates
- Build reliability profiles: accuracy, speed, consistency
- Condition delegation decisions on historical performance
- Use auxiliary rewards for agent optimization

## Key Insight
**Small models + trust modeling = large model performance.** The ability to correctly evaluate peer reliability is more valuable than raw model capability. This suggests we should invest in **tracking and scoring** our sub-agents rather than always using the biggest model.

## Implications for Multi-Agent Systems
- Don't assume all agent outputs are equally reliable
- Build historical performance tracking
- Condition future trust on past behavior
- Small models can punch above weight with proper context
