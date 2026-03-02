import json
import random

random.seed(42)

# Generate samples where summary directly mirrors input content
def make_pair(domain, topic, person, action, urgency):
    # Messy input styles
    inputs = [
        f"uh yeah so {person} brought up {topic}, needs to {action} {urgency}. some back and forth but agreed to move forward.",
        f"Speaker A: Main agenda is {topic}. Speaker B: {person} confirmed {action} is needed {urgency}. Speaker A: Agreed, lets proceed.",
        f"{person} flagged {topic} as priority. action item: {action} {urgency}. team acknowledged.",
        f"quick sync - {topic} came up. {person} said {action} {urgency}. marked as action item.",
        f"{person}: so regarding {topic}, we really need to {action} {urgency}. everyone aligned on this.",
    ]
    # Summary directly references same topic/action/person from input
    targets = [
        f"The team discussed {topic}. {person} will {action} {urgency}.",
        f"The meeting covered {topic}. Key action: {person} to {action} {urgency}.",
        f"{topic} was flagged as a priority. {person} assigned to {action} {urgency}.",
    ]
    return random.choice(inputs), random.choice(targets)

# Rich domain-specific data
meeting_data = [
    # Engineering
    ("engineering", "API integration delays", "backend lead", "fix the authentication bug", "by end of sprint"),
    ("engineering", "deployment pipeline failure", "DevOps team", "restore the staging environment", "asap - critical blocker"),
    ("engineering", "code review backlog", "senior engineer", "review and merge pending PRs", "before Friday release"),
    ("engineering", "database performance issues", "backend team", "optimize slow queries", "urgently - affecting production"),
    ("engineering", "sprint planning", "dev team", "finalize sprint backlog and estimates", "by Monday"),
    ("engineering", "security vulnerability", "security lead", "patch the CVE and deploy fix", "immediately - critical"),
    ("engineering", "technical debt", "engineering manager", "allocate 20% of next sprint to refactoring", "this quarter"),
    ("engineering", "test coverage gaps", "QA team", "write unit tests for payment module", "before release"),
    # Product
    ("product", "Q2 roadmap planning", "product manager", "finalize feature priorities for Q2", "by end of week"),
    ("product", "user onboarding drop-off", "product team", "redesign the onboarding flow", "this sprint - high priority"),
    ("product", "pricing strategy review", "CEO", "decide on new pricing tiers", "before board meeting"),
    ("product", "competitor analysis", "product lead", "complete competitor feature matrix", "by Thursday"),
    ("product", "A/B test results", "data team", "share test results with stakeholders", "this week"),
    ("product", "feature launch readiness", "product manager", "sign off on launch checklist", "asap - launch is Friday"),
    # Marketing
    ("marketing", "Q2 campaign launch", "marketing lead", "finalize campaign assets and copy", "by April 1st deadline"),
    ("marketing", "social media strategy", "content team", "update content calendar for next month", "this week"),
    ("marketing", "ad spend review", "CMO", "reallocate budget from underperforming channels", "urgent - overspending"),
    ("marketing", "brand guidelines update", "design team", "publish updated brand kit", "before new campaign"),
    ("marketing", "customer feedback analysis", "marketing analyst", "compile survey results into report", "by Friday"),
    # Finance
    ("finance", "Q3 budget overrun", "CFO", "identify cost reduction opportunities", "urgent - 15% over budget"),
    ("finance", "investor update preparation", "finance team", "prepare Q2 financial summary", "before board meeting"),
    ("finance", "expense approval backlog", "finance manager", "review and approve pending expense reports", "this week"),
    ("finance", "revenue forecast revision", "CFO", "update Q3 forecast based on new data", "asap"),
    ("finance", "audit preparation", "accounting team", "gather documentation for external audit", "deadline next month"),
    # HR
    ("hr", "engineering hiring plan", "HR lead", "post 3 senior engineer job listings", "asap - critical for roadmap"),
    ("hr", "performance review cycle", "HR manager", "complete reviews for all team members", "overdue - end of quarter"),
    ("hr", "employee onboarding", "HR team", "set up accounts and schedule orientation", "before new joiner start date"),
    ("hr", "team offsite planning", "office manager", "book venue and send invites", "by next Friday"),
    ("hr", "salary review", "HR director", "finalize compensation adjustments", "before end of month"),
    ("hr", "training program rollout", "L&D team", "schedule mandatory compliance training", "this month - required"),
    # Sales
    ("sales", "Q2 pipeline review", "sales lead", "update CRM with latest deal statuses", "before weekly sync"),
    ("sales", "key account at risk", "account manager", "schedule urgent call with client", "asap - contract renewal at risk"),
    ("sales", "new market expansion", "sales director", "research and present market entry plan", "by end of month"),
    ("sales", "sales training", "sales manager", "onboard new reps on product demo", "this week"),
]

synthetic = []
for domain, topic, person, action, urgency in meeting_data:
    # Generate 8 variations per entry
    for _ in range(8):
        inp, tgt = make_pair(domain, topic, person, action, urgency)
        synthetic.append({
            "meeting_id": f"synthetic_{domain}_{topic[:10]}_{_}",
            "input": f"summarize meeting notes: {inp}",
            "target": tgt
        })

random.shuffle(synthetic)
print(f"Generated {len(synthetic)} high-quality synthetic samples")
print("\nSample input:", synthetic[0]["input"])
print("Sample target:", synthetic[0]["target"])

# Load AMI data
with open("ami_train.json") as f: ami_train = json.load(f)
with open("ami_val.json") as f: ami_val = json.load(f)
with open("ami_test.json") as f: ami_test = json.load(f)

# Merge
augmented_train = ami_train + synthetic[:int(len(synthetic)*0.9)]
augmented_val = ami_val + synthetic[int(len(synthetic)*0.9):]
random.shuffle(augmented_train)

with open("aug_train.json", "w") as f: json.dump(augmented_train, f, indent=2)
with open("aug_val.json", "w") as f: json.dump(augmented_val, f, indent=2)
with open("aug_test.json", "w") as f: json.dump(ami_test, f, indent=2)

print(f"\nAugmented train: {len(augmented_train)} samples")
print(f"Augmented val:   {len(augmented_val)} samples")
print(f"Test (AMI only): {len(ami_test)} samples")
print("Saved: aug_train.json, aug_val.json, aug_test.json")