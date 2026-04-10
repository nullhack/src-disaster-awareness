---
name: media-monitor
description: Guidelines for monitoring media coverage and public discussions related to disasters, humanitarian aid, and Singapore Red Cross response
compatibility: "1.0.0+"
metadata:
  category: monitoring
  difficulty: intermediate
  type: media-monitoring
---

# Media Monitor Skill

Guidelines for monitoring news sources and social media platforms for disaster-related coverage and discussions relevant to Singapore and the Singapore Red Cross (SRC).

## General Monitoring Overview

### Purpose
Monitor reliable and credible news sources and social media platforms for media coverage or public discussions related to disasters that may be relevant to:
- Singapore or Singapore citizens
- Singapore Red Cross (SRC) humanitarian response
- Public concerns about humanitarian aid and donations

### Monitoring Scope

**Geographic Focus (Peacetime):**
- Asia Pacific region (primary)
- Secondary global attention to major crises

**Monitoring Frequency:**
- **Peacetime**: 2-3 monitoring scans per week (30-45 mins each)
- **Emergency/Major Global Crisis**: Daily monitoring scans (30-60 mins)

### Credible News Sources

**Tier 1 - International News Agencies:**
- Reuters
- Associated Press (AP)
- BBC News
- Agence France-Presse (AFP)
- Al Jazeera

**Tier 2 - Regional News Outlets:**
- Channel NewsAsia
- The Straits Times
- The Star (Malaysia)
- Antara News (Indonesia)
- Bangkok Post
- Manila Times
- The Indian Express

**Tier 3 - Specialized Disaster/Humanitarian Coverage:**
- ReliefWeb
- Humanitarian News and Analysis
- Devex
- AlertNet

**Social Media Platforms to Monitor:**
- Twitter/X (using relevant hashtags)
- Facebook (SRC official page and Singapore-related groups)
- WhatsApp (official SRC channels)
- TikTok (for trending disaster-related content in Singapore)
- Reddit (r/Singapore, regional subreddits)

## General Monitoring Guidelines

### Content to INCLUDE in Reports

✅ **Singapore or SRC Mentioned**
- Articles explicitly mentioning Singapore
- Content referencing Singapore citizens affected
- SRC involvement in response or relief efforts
- Singapore government statements about aid

Example: "Singapore Red Cross announces $500,000 donation to earthquake relief"

✅ **Public Concerns - Donation/Aid Related**
- Questions about how to donate
- Criticism of aid response (adequacy, timeliness)
- Public discussions about SRC transparency
- Fundraising appeals and results

Example: "How can Singaporeans help? Ways to donate to Pakistan floods relief"

✅ **Misinformation Flagging**
- False reports about disaster scale/impact
- Fake donation links or scams
- Conspiracy theories spreading in Singapore
- Misleading aid information

Example: "Singapore fraud alert: Fake charity collecting funds for Myanmar donation scams"

✅ **Public Sentiment on Humanitarian Issues**
- Singapore community response to regional disasters
- Online discussions about aid effectiveness
- Donor concerns and questions
- Media coverage of SRC campaigns

### Content to EXCLUDE from Reports

❌ **General International News**
- Disaster coverage with no Singapore connection
- International aid from other countries (unless Singapore involved)
- Generic disaster reporting without Singapore angle

❌ **Misinformation (without Singapore relevance)**
- False reports in foreign media
- Unverified claims not affecting Singapore audience

❌ **Commercial Content**
- Sponsored ads for disaster-related products
- Travel warnings unrelated to humanitarian concerns
- Insurance/investment content

## Report Submission Format

### General Monitoring Reports (WhatsApp Chat)

**Report Format:**
```
[Country / Disaster]
[Link]
[Optional flags if relevant]
```

**Example:**
```
Sri Lanka – floods
https://www.channelnewsasia.com/asia/sri-lanka-floods-2025
[SRC mentioned]
```

**Optional Flags:**
- `[SRC mentioned]` - SRC involved or quoted
- `[Singapore aid]` - Singapore government response
- `[Donation concerns]` - Public questions about giving
- `[Misinformation]` - Fake news alert
- `[High priority]` - Urgent public concern

### Disaster-Specific Monitoring (Disaster Event Timeline Document)

When SRC is supporting or closely monitoring a disaster, media monitoring is documented in the "Media & Public Discussion Monitoring" tab of the Disaster Event Timeline document.

**Report Structure:**
```
Country: [Country Name]
Date of Report: [YYYY-MM-DD]
Province/State: [Location]
Details (incl. source): [Summary of content]
SRC Mentioned: Yes/No
Public Concern - Donation/Aid: Yes/No
```

**Example Entry:**
```
Country: Indonesia
Date of Report: 2025-12-28
Province/State: Aceh
Details: Updates on flood response efforts, 25 water trucks deployed by government
Source: https://en.antaranews.com/news/397840/indonesia-sends-25-water-trucks-to-aceh-after-floods-landslides
SRC Mentioned: No
Public Concern - Donation/Aid: No
```

## Peacetime Monitoring Process

### Weekly Monitoring Scan (30-45 mins)

**Step 1: News Aggregator Check (10 mins)**
- Google News: Search "disaster" + region keywords
- Check Reuters, BBC, AP for breaking news
- Review ReliefWeb latest updates

**Step 2: Asia Pacific Specific Search (10 mins)**
- Search "[Country] disaster" for each Group A country
- Review Channel NewsAsia, Straits Times
- Check regional news outlets (The Star, Bangkok Post, etc.)

**Step 3: SRC and Singapore Angle (10 mins)**
- Search "Singapore Red Cross" + "donation/relief"
- Check SRC official social media
- Monitor Singapore news for aid announcements

**Step 4: Social Media Scan (5-10 mins)**
- Twitter: Search disaster-related hashtags (#DisasterResponse, #HelpNeeded, etc.)
- Facebook: Check SRC page comments and discussions
- Reddit: Check r/Singapore and regional communities

**Step 5: Submit Reports**
- Share links to WhatsApp "media updates" group
- Use standardized format
- Include relevant flags

### Daily Monitoring (During Emergency)

When a major disaster with SRC involvement is active:

**Frequency:** Once daily (30-60 mins)

**Process:**
1. Check news sources for new developments
2. Look for SRC operational updates
3. Monitor for donation concerns or scams
4. Track public sentiment on aid response
5. Document in Disaster Event Timeline
6. Flag urgent issues in WhatsApp chat

**Post-Emergency Transition:**
- When crisis stabilizes, return to weekly scans
- Continue documenting media coverage in Disaster Event Timeline
- Monitor for long-term impact stories

## Sentiment and Tone Analysis (Optional)

While not required, you may note:

**Positive sentiment indicators:**
- Praise for aid effectiveness
- High donor participation
- Community solidarity stories
- Successful relief operations

**Negative sentiment indicators:**
- Criticism of aid response
- Donation concerns
- Reports of insufficient help
- Misinformation spreading

**Neutral/Informational:**
- Updates on disaster progression
- Operational information
- Statistics and data

## Red Flags and Escalation

Immediately flag in WhatsApp if:

🚨 **Scams/Misinformation**
- Fake donation links circulating
- False reports about disaster scale
- Conspiracy theories gaining traction
- Impersonation of SRC or aid organizations

🚨 **Significant Public Concerns**
- Overwhelming donation questions
- Major criticism of SRC response
- Media questioning aid adequacy
- Trust/transparency issues emerging

🚨 **Crisis Escalation**
- Disaster impact larger than expected
- New secondary impacts emerging
- Regional spread of emergency
- Sudden surge in Singapore-related cases/impact

🚨 **Humanitarian Crisis Declaration**
- Official humanitarian crisis announcement
- International aid appeal
- Large-scale displacement
- Significant loss of life

## Data Recording

For all disaster-specific monitoring, record:

```json
{
  "monitoring_date": "YYYY-MM-DD",
  "disaster_name": "Event identifier",
  "article_title": "Title of article/post",
  "source_url": "Link to content",
  "source_type": "News article / Social media post / Official statement / Other",
  "src_mentioned": true/false,
  "donation_related": true/false,
  "misinformation": true/false,
  "key_points": [
    "Summary point 1",
    "Summary point 2"
  ],
  "sentiment": "positive / neutral / negative",
  "urgency": "routine / important / urgent",
  "action_taken": "submitted to WhatsApp / added to timeline / flagged for escalation"
}
```

## Best Practices

1. **Verify before sharing** - Check multiple sources
2. **Use credible outlets** - Stick to Tier 1-2 sources
3. **Be timely** - Report breaking news quickly
4. **Provide context** - Explain why it's relevant to Singapore
5. **Avoid speculation** - Report facts, not assumptions
6. **Respect privacy** - Don't amplify misinformation
7. **Stay organized** - Use standardized formats
8. **Flag concerns** - Escalate unusual patterns
9. **Document everything** - Keep records for analysis
10. **Update regularly** - Keep timeline current during emergencies

## Common Keywords for Searching

**Disaster-related:**
- disaster, emergency, crisis, tragedy, catastrophe
- earthquake, flood, typhoon, cyclone, hurricane, tornado
- wildfire, landslide, volcano, tsunami, avalanche
- outbreak, epidemic, pandemic, disease

**Singapore/SRC-related:**
- Singapore, SRC, Red Cross
- Singapore aid, Singapore donation
- Singaporean, Singapore citizens
- Singapore government response

**Aid/Donation-related:**
- relief, humanitarian, aid, assistance
- donation, fundraising, appeal, contribute
- charity, volunteer, support, help

## Tools and Resources

**Recommended Monitoring Tools:**
- Google News Alerts (custom searches)
- Twitter Advanced Search
- RSS Feed readers (for news agencies)
- TweetDeck (for real-time Twitter monitoring)
- Reddit search (for community discussion)

**Browser Extensions:**
- News aggregators
- Fact-checking tools
- Translation tools (for non-English sources)

## Archiving and Documentation

Maintain records of:
- All submitted reports
- Links to sources
- Dates of monitoring
- Relevant flag history
- Changes in incident status
- Public sentiment trends

This allows for:
- Performance tracking
- Pattern analysis
- Historical reference
- SRC communication planning
- Donor engagement strategy
