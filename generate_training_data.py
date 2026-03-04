"""
generate_training_data.py
Generates 1000+ high quality messy->clean pairs for fine-tuning flan-t5-base.
Domains: engineering, product, finance, HR, marketing
"""

import json
import random

random.seed(42)

# ─── Clean templates per domain ───────────────────────────────────────────────

ENGINEERING = [
    ("api integration is broken since last night's deployment. cannot process payments before market opens tomorrow. critical fix required.", "api intgration still brken since lst nite deploy cant process any paymnts before mkt opens tmrw critical"),
    ("ssl certificate expires in 2 days. if it lapses the entire site goes down. needs renewal immediately.", "ssl cert expirng in 2 days if it goes down whole site dies needs renewl asap"),
    ("database migration script is ready and waiting for approval to run on production. sign off needed before end of day.", "db migration script rdy waitng 4 approval 2 run on prod needs sign off b4 eod"),
    ("checkout flow has a 3 second lag affecting all users. slow query flagged by backend team. needs investigation.", "checkout flow 3sec lag all users slow query flagged by backend investigate pls"),
    ("backend service is down and blocking all deployments. devops needs to investigate and restore immediately.", "backend service dwn blocking all deploys devops needs 2 investigate restore asap"),
    ("memory leak detected in production causing server crashes every 6 hours. engineering team must patch before next release.", "memory leak in prod causing server crash every 6hrs eng team must patch b4 next release"),
    ("ci cd pipeline is failing on all pull requests. blocking the entire team from merging. needs immediate fix.", "cicd pipeline failng on all prs blocking whole team frm merging needs fix asap"),
    ("load balancer misconfigured after last deployment. causing 503 errors for 30 percent of users. must be rolled back.", "load balancer misconfigured after last deploy causing 503 errors for 30pct users must rollback"),
    ("security vulnerability found in authentication module. must be patched before end of sprint. high priority.", "security vuln found in auth module must patch b4 end of sprint high priority"),
    ("redis cache is not invalidating properly causing stale data issues for users. backend to investigate.", "redis cache not invalidating properly causing stale data for users backend investigate"),
    ("mobile app crashes on ios 17 for users with large datasets. needs hotfix before app store review deadline.", "mobile app crashing on ios17 for users w large datasets needs hotfix b4 appstore review deadline"),
    ("docker container memory limit too low causing oom kills in staging. devops to update resource limits.", "docker container mem limit 2 low causing oom kills in staging devops update resource limits"),
    ("third party payment gateway returning timeout errors since 2am. affecting all checkout flows. urgent escalation needed.", "3rd party payment gateway returning timeout errors since 2am affecting all checkout flows urgent escalation"),
    ("websocket connections dropping after 60 seconds causing real time features to fail. backend team to investigate.", "websocket connections dropping after 60s causing realtime features to fail backend investigate"),
    ("database connection pool exhausted during peak hours causing request failures. needs tuning.", "db connection pool exhausted during peak hrs causing req failures needs tuning"),
    ("api rate limiting not working correctly. some clients exceeding limits without being throttled. security concern.", "api rate limiting not working correctly some clients exceeding limits w/o being throttled security concern"),
    ("elasticsearch index corrupted after power outage. search feature down for all users. needs rebuild.", "elasticsearch idx corrupted after power outage search feature down for all users needs rebuild"),
    ("staging environment out of sync with production. causing false test results. devops to sync environments.", "staging env out of sync w prod causing false test results devops sync envs"),
    ("new microservice deployment failing due to missing environment variables. devops to add to config.", "new microservice deploy failing due 2 missing env vars devops add 2 config"),
    ("graphql query taking 8 seconds for dashboard load. needs optimization before demo next week.", "graphql query taking 8s for dashboard load needs optimization b4 demo next wk"),
]

PRODUCT = [
    ("onboarding dropout rate has hit 60 percent. new enterprise clients are leaving during setup. product team should investigate and fix.", "onboarding drpout rate hit 60pct new enterpise clients leavng during setup product team shld fix this"),
    ("retro notes from last week still not shared with the team. someone needs to send them out.", "retro notes frm lst wk still not shared wit the team"),
    ("new hire still has no laptop and no system access on day 3. someone needs to sort this out immediately.", "new hire still no laptop no access 3rd day wtf someone needs 2 sort this out"),
    ("product roadmap for q3 has not been finalized. stakeholders are waiting for sign off. needs to be done by friday.", "product roadmap for q3 not finalized stakeholders waiting for sign off needs done by fri"),
    ("user research sessions scheduled for next week have no confirmed participants. ux team needs to recruit urgently.", "user research sessions scheduled nxt wk have no confirmed participants ux team needs 2 recruit urgently"),
    ("feature flag for new dashboard is still enabled in production after rollout completed. needs to be cleaned up.", "feature flag for new dashboard still enabled in prod after rollout completed needs cleanup"),
    ("competitor launched a similar feature yesterday. product team needs to review and assess impact on roadmap.", "competitor launched similar feature yesterday product team needs 2 review and assess impact on roadmap"),
    ("a/b test results for new onboarding flow are ready. product team needs to review and make go no go decision.", "ab test results for new onboarding flow are ready product team needs 2 review and make go nogo decision"),
    ("sprint backlog has 40 ungroomed tickets. product manager needs to prioritize before planning session monday.", "sprint backlog has 40 ungroomed tickets pm needs 2 prioritize b4 planning session monday"),
    ("customer feedback from last quarter has not been triaged. product team needs to review and action items identified.", "customer feedback from last qtr has not been triaged product team needs 2 review and action items identified"),
    ("design mockups for mobile app redesign are overdue by 2 weeks. designer needs to deliver by end of week.", "design mockups for mobile app redesign overdue by 2wks designer needs 2 deliver by end of wk"),
    ("product spec for new billing module is incomplete. engineering cannot start without it. product manager to complete.", "product spec for new billing module incomplete engineering cant start without it pm to complete"),
    ("user acceptance testing for v2 release not started. launch date is in 10 days. qa team to begin immediately.", "user acceptance testing for v2 release not started launch date is in 10 days qa team begin immediately"),
    ("nps survey results show 30 percent drop in satisfaction. product team to analyze and present findings by thursday.", "nps survey results show 30pct drop in satisfaction product team analyze and present findings by thu"),
    ("product demo to enterprise client scheduled for tuesday. demo environment is not set up. needs to be ready by monday.", "product demo to enterprise client scheduled tuesday demo env not set up needs ready by monday"),
]

FINANCE = [
    ("q2 infrastructure budget needs cfo approval by friday or the team will lose the cloud credits.", "q2 infra budget needs cfo approval by fri or we lose the cloud credits"),
    ("invoice for aws services is 40 percent over budget this month. finance team needs to review cloud spending.", "invoice for aws services 40pct over budget this month finance team needs 2 review cloud spending"),
    ("vendor contract renewal is due in 2 weeks. legal and finance need to review terms before signing.", "vendor contract renewal due in 2wks legal and finance need 2 review terms b4 signing"),
    ("expense reports from q1 have not been submitted by 3 team members. finance team to follow up.", "expense reports from q1 not submitted by 3 team members finance team follow up"),
    ("budget forecast for next fiscal year is overdue. finance team to deliver to board by end of month.", "budget forecast for next fiscal yr overdue finance team deliver 2 board by end of month"),
    ("payment to key vendor is 15 days overdue. accounts payable to process immediately to avoid service disruption.", "payment to key vendor 15 days overdue accounts payable process immediately avoid service disruption"),
    ("monthly burn rate has increased by 25 percent. cfo needs to review headcount and infrastructure costs.", "monthly burn rate increased by 25pct cfo needs 2 review headcount and infra costs"),
    ("tax filing deadline is in 3 weeks. finance team needs all receipts and documentation submitted by next friday.", "tax filing deadline in 3wks finance team needs all receipts and docs submitted by nxt fri"),
    ("procurement approval for new software licenses is pending since last month. needs cto and cfo sign off.", "procurement approval for new software licenses pending since last month needs cto and cfo sign off"),
    ("annual audit preparation has not started. auditors arrive in 4 weeks. finance team to begin document collection.", "annual audit prep has not started auditors arrive in 4wks finance team begin doc collection"),
]

HR = [
    ("management thinks clark has not been active for the last three meetings. hr should follow up.", "management thinks clark has not been um active for the last uh ah maybe for last three meetings"),
    ("performance review cycle starts next monday. all managers must complete reviews by end of month.", "perf review cycle starts nxt monday all managers must complete reviews by end of month"),
    ("3 open engineering positions have been unfilled for 60 days. hr to escalate recruiting efforts immediately.", "3 open eng positions unfilled for 60 days hr escalate recruiting efforts immediately"),
    ("new employee orientation for 5 starters next week has no agenda prepared. hr to finalize by thursday.", "new employee orientation for 5 starters nxt wk has no agenda prepared hr finalize by thu"),
    ("benefits enrollment deadline is friday. 12 employees have not yet enrolled. hr to send reminder today.", "benefits enrollment deadline is fri 12 employees not yet enrolled hr send reminder today"),
    ("workplace incident report from last tuesday has not been filed. hr must submit to compliance team by end of day.", "workplace incident report from last tue not filed hr must submit 2 compliance team by eod"),
    ("salary benchmarking study is 3 months overdue. hr to present findings to leadership by next friday.", "salary benchmarking study 3 months overdue hr present findings 2 leadership by nxt fri"),
    ("team offsite planning for q3 has not started. hr to propose venue and agenda options by next week.", "team offsite planning for q3 not started hr propose venue and agenda options by nxt wk"),
    ("remote work policy update has been pending legal review for 6 weeks. hr to follow up with legal team.", "remote work policy update pending legal review for 6wks hr follow up w legal team"),
    ("exit interview data from last quarter has not been analyzed. hr to present retention insights to leadership.", "exit interview data from last qtr not analyzed hr present retention insights 2 leadership"),
]

MARKETING = [
    ("q3 campaign assets are not ready for launch next monday. marketing team needs to deliver by friday.", "q3 campaign assets not ready for launch nxt monday marketing team needs 2 deliver by fri"),
    ("social media content calendar for next month has not been created. marketing to complete by end of week.", "social media content calendar for nxt month not created marketing complete by end of wk"),
    ("email campaign to enterprise segment has a broken unsubscribe link. needs to be fixed before next send.", "email campaign to enterprise segment has broken unsubscribe link needs fix b4 next send"),
    ("website landing page conversion rate dropped 20 percent last week. marketing to investigate and optimize.", "website landing page conversion rate dropped 20pct last wk marketing investigate and optimize"),
    ("press release for product launch has not been approved by legal. launch is in 5 days. needs sign off today.", "press release for product launch not approved by legal launch in 5 days needs sign off today"),
    ("google ads budget overspent by 35 percent this month. marketing team to pause campaigns and review.", "google ads budget overspent by 35pct this month marketing team pause campaigns and review"),
    ("influencer partnership contract unsigned 2 weeks before campaign start. marketing to follow up immediately.", "influencer partnership contract unsigned 2wks b4 campaign start marketing follow up immediately"),
    ("brand guidelines document not updated after rebrand 3 months ago. marketing to update and distribute.", "brand guidelines doc not updated after rebrand 3 months ago marketing update and distribute"),
    ("product demo video for trade show has not been produced. event is in 3 weeks. video team to start immediately.", "product demo video for trade show not produced event in 3wks video team start immediately"),
    ("seo audit findings from last month have not been actioned. organic traffic down 15 percent. marketing to prioritize.", "seo audit findings from last month not actioned organic traffic down 15pct marketing prioritize"),
]

# ─── Typo and shorthand generators ────────────────────────────────────────────

TYPOS = {
    "the": ["teh", "th", "the"],
    "and": ["nd", "an", "adn"],
    "with": ["wit", "w", "wth"],
    "before": ["b4", "bfore", "befre"],
    "because": ["bcuz", "becuz", "bc"],
    "should": ["shld", "shoud", "shuld"],
    "needs": ["neds", "ned", "needs"],
    "meeting": ["meetng", "meting", "mtg"],
    "integration": ["intgration", "integation", "integraton"],
    "immediately": ["immediatly", "immedately", "asap"],
    "deployment": ["deploy", "deplmt", "depoy"],
    "production": ["prod", "producton", "prodcution"],
    "infrastructure": ["infra", "infrastracture", "infrastrcutre"],
    "approval": ["aprvl", "appoval", "aproval"],
    "investigation": ["investgation", "investigaton", "investig"],
    "performance": ["perf", "perfomance", "performnce"],
    "department": ["dept", "deparment", "departmnt"],
    "management": ["mgmt", "managment", "managemnt"],
    "available": ["avail", "availble", "availabe"],
    "tomorrow": ["tmrw", "tomrw", "tomorow"],
    "today": ["2day", "tday", "toady"],
    "please": ["pls", "plz", "pleas"],
    "something": ["smthng", "somthing", "soemthing"],
    "everyone": ["evry1", "evryone", "everone"],
    "already": ["alrdy", "alredy", "alreay"],
    "important": ["imprtant", "importnt", "imp"],
    "probably": ["prob", "probly", "prolly"],
    "through": ["thru", "thrugh", "thro"],
    "though": ["tho", "thogh", "thugh"],
    "without": ["w/o", "witout", "withut"],
    "people": ["ppl", "peple", "pepole"],
    "working": ["wrkng", "workng", "wrking"],
    "waiting": ["waitng", "waitin", "wating"],
    "looking": ["lookng", "lookin", "loking"],
    "getting": ["getng", "gettin", "geting"],
    "going": ["gng", "goin", "goign"],
    "trying": ["tryng", "tryin", "trying"],
    "having": ["havng", "havin", "haveing"],
    "coming": ["comng", "comin", "comeing"],
    "taking": ["takng", "takin", "takeing"],
}

FILLER_WORDS = [
    "um ", "uh ", "ah ", "like ", "you know ", "basically ", "literally ",
    "so ", "well ", "i mean ", "right ", "okay so ", "yeah so ",
]

def add_typos(text, rate=0.15):
    words = text.split()
    result = []
    for word in words:
        clean = word.lower().rstrip('.,!?')
        if clean in TYPOS and random.random() < rate:
            result.append(random.choice(TYPOS[clean]))
        else:
            result.append(word)
    return ' '.join(result)

def add_fillers(text, n=2):
    words = text.split()
    positions = random.sample(range(len(words)), min(n, len(words)))
    for pos in sorted(positions, reverse=True):
        words.insert(pos, random.choice(FILLER_WORDS).strip())
    return ' '.join(words)

def make_messy(clean_text):
    """Apply random transformations to make clean text messy."""
    text = clean_text.lower()
    text = add_typos(text, rate=0.2)
    if random.random() < 0.4:
        text = add_fillers(text, n=random.randint(1, 3))
    # Remove some punctuation
    if random.random() < 0.5:
        text = text.replace('.', '').replace(',', '')
    # Replace numbers
    text = text.replace('two', '2').replace('three', '3').replace('four', '4')
    return text.strip()

# ─── Generate dataset ──────────────────────────────────────────────────────────

def generate_dataset():
    all_pairs = []

    # Use original pairs from all domains
    all_templates = ENGINEERING + PRODUCT + FINANCE + HR + MARKETING

    # Add original pairs
    for clean, messy in all_templates:
        all_pairs.append({
            "input": f"summarize meeting notes: {messy}",
            "target": clean
        })

    # Generate augmented variants
    for clean, messy in all_templates:
        for _ in range(16):  # 16 variants per template
            augmented_messy = make_messy(clean)
            all_pairs.append({
                "input": f"summarize meeting notes: {augmented_messy}",
                "target": clean
            })

    random.shuffle(all_pairs)

    # Split 80/10/10
    n = len(all_pairs)
    train = all_pairs[:int(n * 0.8)]
    val = all_pairs[int(n * 0.8):int(n * 0.9)]
    test = all_pairs[int(n * 0.9):]

    json.dump(train, open('aug_train_v2.json', 'w'), indent=2)
    json.dump(val, open('aug_val_v2.json', 'w'), indent=2)
    json.dump(test, open('aug_test_v2.json', 'w'), indent=2)

    print(f"Total pairs: {n}")
    print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
    print("\nSample pair:")
    print(f"INPUT:  {train[0]['input']}")
    print(f"TARGET: {train[0]['target']}")

if __name__ == "__main__":
    generate_dataset()
