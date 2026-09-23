"""Generator for Auto Bot LinkedIn Job n8n Workflow JSON."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "n8n" / "auto_bot_linkedin_job.json"

nodes = [
    {
        "id": "1",
        "name": "Daily Hunt",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [100, 300],
        "parameters": {
            "rule": {
                "interval": [
                    {"field": "cronExpression", "expression": "30 13 * * *"}
                ]
            }
        }
    },
    {
        "id": "2",
        "name": "Telegram Command",
        "type": "n8n-nodes-base.telegramTrigger",
        "typeVersion": 1.1,
        "position": [100, 500],
        "parameters": {
            "updates": ["message", "callback_query"]
        },
        "credentials": {
            "telegramApi": {
                "id": "telegram_cred",
                "name": "Telegram account"
            }
        }
    },
    {
        "id": "3",
        "name": "Parse Telegram Command",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [320, 500],
        "parameters": {
            "jsCode": """const j = $json;
const msg = j.message || {};
const cb = j.callback_query;
if (cb && cb.data) {
  const [action, listing_id] = String(cb.data).split('::');
  return [{ json: { route: action, listing_id,
    chatId: cb.message.chat.id, callback_id: cb.id } }];
}
const text = (msg.text || '').trim();
const route = text.startsWith('/status') ? 'status'
  : text.startsWith('/help') ? 'help' : 'hunt';
return [{ json: { route, chatId: msg.chat && msg.chat.id } }];"""
        }
    },
    {
        "id": "4",
        "name": "Route Command",
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3,
        "position": [540, 500],
        "parameters": {
            "rules": {
                "values": [
                    {"value1": "={{ $json.route }}", "value2": "hunt", "operation": "equals"},
                    {"value1": "={{ $json.route }}", "value2": "status", "operation": "equals"},
                    {"value1": "={{ $json.route }}", "value2": "help", "operation": "equals"},
                    {"value1": "={{ $json.route }}", "value2": "draft", "operation": "equals"},
                    {"value1": "={{ $json.route }}", "value2": "open", "operation": "equals"},
                    {"value1": "={{ $json.route }}", "value2": "contact", "operation": "equals"}
                ]
            }
        }
    },
    {
        "id": "5",
        "name": "Telegram Help",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [780, 650],
        "parameters": {
            "chatId": "={{ $json.chatId }}",
            "text": """Auto Bot LinkedIn Job
/hunt — search and score US listings now
/status — today's keep / hot / credits
/help — this message

On each card:
Draft outreach — write a note (blocked during company cooldown)
Open posting — open the job URL
Find contact — LinkedIn search for the approach role

Nothing is sent to a company unless you paste the draft yourself."""
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    {
        "id": "6",
        "name": "Hunt Config",
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [780, 300],
        "parameters": {
            "options": {},
            "fields": {
                "values": [
                    {"name": "operator_name", "stringValue": "Operator"},
                    {"name": "cooldown_days", "numberValue": 21},
                    {"name": "keep_score_min", "numberValue": 55},
                    {"name": "hot_score_min", "numberValue": 80},
                    {"name": "posted_within_days", "numberValue": 1},
                    {"name": "posted_within_hours", "numberValue": 24},
                    {"name": "jobspipe_limit", "numberValue": 25},
                    {"name": "description_max_chars", "numberValue": 6000},
                    {
                        "name": "keywords_include",
                        "stringValue": "Forward Deployed, Forward Deployed Engineer, Forward Deployed AI, AI Solutions Engineer, GenAI Solutions Engineer, GenAI Engineer, Generative AI Engineer, LLM Engineer, AI Agent Engineer, AI Systems Engineer, AI Application Developer, Full Stack AI Engineer, Applied AI Engineer, RAG Engineer, Prompt Engineer, Machine Learning Engineer, AI Software Engineer, Founding AI Engineer, Founding Software Developer, AI Engineer, Python AI Developer, AI Developer"
                    },
                    {
                        "name": "keywords_exclude_title",
                        "stringValue": "Hardware Engineer, Mechanical Engineer, Civil Engineer, Nurse, Therapist, Psychotherapist, Dental, Accountant, Payroll, Customer Service, Customer Support, Sales Representative, Account Executive, Retail, Legal Counsel, Recruiter, Talent Partner, Project Scheduler, Billing Specialist"
                    },
                    {
                        "name": "agency_name_hints",
                        "stringValue": "recruitment, recruiting, staffing, search firm, talent partners"
                    }
                ]
            }
        }
    },
    {
        "id": "7",
        "name": "Build JobsPipe Payload",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1000, 180],
        "parameters": {
            "jsCode": """return [{
  json: {
    job_title_or: ["Forward Deployed Engineer", "AI Solutions Engineer", "GenAI Engineer"],
    job_country_code_or: ["US"],
    posted_at_max_age_days: 1,
    limit: 25,
    include_total_results: true
  }
}];"""
        }
    },
    {
        "id": "8",
        "name": "JobsPipe Search",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1220, 180],
        "parameters": {
            "method": "POST",
            "url": "https://api.jobspipe.dev/v1/jobs/search",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($json) }}",
            "options": {"timeout": 20000}
        },
        "continueOnFail": True,
        "credentials": {"httpHeaderAuth": {"id": "jobspipe_cred", "name": "JobsPipe Header Auth"}}
    },
    {
        "id": "9",
        "name": "Remotive Feed",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1220, 300],
        "parameters": {
            "method": "GET",
            "url": "https://remotive.com/api/remote-jobs",
            "options": {"timeout": 20000}
        },
        "continueOnFail": True
    },
    {
        "id": "10",
        "name": "RemoteOK Feed",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1220, 420],
        "parameters": {
            "method": "GET",
            "url": "https://remoteok.com/api",
            "options": {"timeout": 20000}
        },
        "continueOnFail": True
    },
    {
        "id": "11",
        "name": "Arbeitnow Feed",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1220, 540],
        "parameters": {
            "method": "GET",
            "url": "https://www.arbeitnow.com/api/job-board-api",
            "options": {"timeout": 20000}
        },
        "continueOnFail": True
    },
    {
        "id": "12",
        "name": "Jobicy Feed",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1220, 660],
        "parameters": {
            "method": "GET",
            "url": "https://jobicy.com/api/v2/remote-jobs",
            "options": {"timeout": 20000}
        },
        "continueOnFail": True
    },
    {
        "id": "13",
        "name": "Merge All Sources",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1460, 300],
        "parameters": {
            "jsCode": """function norm(s) {
  return String(s || '').toLowerCase().replace(/&/g,'and').replace(/[^a-z0-9]+/g,' ').trim();
}
function companyKey(s) {
  return norm(s).replace(/\\b(pvt|private|ltd|limited|inc|llc|llp|gmbh|plc)\\b/g,'').trim();
}

const out = [];

// 1. JobsPipe
try {
  const jp = $('JobsPipe Search').first().json || {};
  const data = jp.data || [];
  for (const it of data) {
    out.push({
      listing_id: 'jobspipe:' + (it.id || ''),
      fingerprint: companyKey(it.company) + '|' + norm(it.job_title),
      source: 'jobspipe',
      title: it.job_title || '',
      company: it.company || '',
      location: it.location || '',
      country: it.country_code || 'US',
      remote: !!it.remote,
      employment_type: it.seniority || '',
      posted_at: it.date_posted || '',
      url: it.source_url || '',
      description: it.description || ''
    });
  }
} catch (e) {}

// 2. Remotive
try {
  const rem = $('Remotive Feed').first().json || {};
  for (const it of (rem.jobs || [])) {
    out.push({
      listing_id: 'remotive:' + (it.id || ''),
      fingerprint: companyKey(it.company_name) + '|' + norm(it.title),
      source: 'remotive',
      title: it.title || '',
      company: it.company_name || '',
      location: it.candidate_required_location || '',
      country: '',
      remote: true,
      employment_type: it.job_type || '',
      posted_at: it.publication_date || '',
      url: it.url || '',
      description: it.description || ''
    });
  }
} catch (e) {}

// 3. RemoteOK
try {
  const rok = $('RemoteOK Feed').all() || [];
  for (const row of rok) {
    const it = row.json;
    if (it && it.id && it.position) {
      out.push({
        listing_id: 'remoteok:' + it.id,
        fingerprint: companyKey(it.company) + '|' + norm(it.position),
        source: 'remoteok',
        title: it.position || '',
        company: it.company || '',
        location: it.location || '',
        country: '',
        remote: true,
        employment_type: '',
        posted_at: it.date || '',
        url: it.url || '',
        description: it.description || ''
      });
    }
  }
} catch (e) {}

// 4. Arbeitnow
try {
  const arb = $('Arbeitnow Feed').first().json || {};
  for (const it of (arb.data || [])) {
    out.push({
      listing_id: 'arbeitnow:' + (it.slug || it.url || ''),
      fingerprint: companyKey(it.company_name) + '|' + norm(it.title),
      source: 'arbeitnow',
      title: it.title || '',
      company: it.company_name || '',
      location: it.location || '',
      country: '',
      remote: !!it.remote,
      employment_type: '',
      posted_at: it.created_at || '',
      url: it.url || '',
      description: it.description || ''
    });
  }
} catch (e) {}

// 5. Jobicy
try {
  const jobicy = $('Jobicy Feed').first().json || {};
  for (const it of (jobicy.jobs || [])) {
    out.push({
      listing_id: 'jobicy:' + (it.id || ''),
      fingerprint: companyKey(it.companyName) + '|' + norm(it.jobTitle),
      source: 'jobicy',
      title: it.jobTitle || '',
      company: it.companyName || '',
      location: it.jobGeo || '',
      country: '',
      remote: true,
      employment_type: it.jobType || '',
      posted_at: it.pubDate || '',
      url: it.url || '',
      description: it.jobDescription || ''
    });
  }
} catch (e) {}

return out.map(j => ({ json: j }));"""
        }
    },
    {
        "id": "14",
        "name": "Normalize Listings",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1680, 300],
        "parameters": {
            "jsCode": """const cfg = $('Hunt Config').first().json;
const hints = (cfg.agency_name_hints || '').toLowerCase().split(',').map(s => s.trim());

return $input.all().map(item => {
  const j = item.json;
  const combined = (j.company + ' ' + j.title).toLowerCase();
  const agency_suspect = hints.some(h => h && combined.includes(h));
  return { json: { ...j, agency_suspect } };
});"""
        }
    },
    {
        "id": "15",
        "name": "Drop Non-US",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1880, 300],
        "parameters": {
            "jsCode": """const NON_US = /\\b(london|bengaluru|bangalore|uk|united kingdom|india|germany|singapore|berlin|paris|france|canada|toronto|vancouver|australia|sydney|melbourne|netherlands|amsterdam|emea|latam|apac|brazil|mexico|poland|spain|madrid|barcelona|ireland|dublin|japan|tokyo)\\b/i;
const US_PAT = /\\b(united states|usa|u\\.s\\.a?|u\\.s\\.|\\b[A-Z]{2}\\b\\s+remote|us-remote|remote,\\s*us|remote\\s*\\(us\\)|us\\s+only|anywhere\\s+in\\s+the\\s+us)\\b/i;

return $input.all().filter(item => {
  const j = item.json;
  const c = String(j.country || '').trim().toUpperCase();
  const loc = String(j.location || '').trim();

  if (c && c !== 'US' && c !== 'USA' && c !== 'UNITED STATES') return false;
  if (NON_US.test(loc)) return false;
  if (c === 'US' || c === 'USA' || c === 'UNITED STATES') return true;
  if (US_PAT.test(loc)) return true;
  if (j.remote) {
    const locL = loc.toLowerCase();
    if (!loc || locL.includes('remote') || !locL.includes('worldwide')) {
      if (locL.includes('worldwide') || locL.includes('global') || locL.includes('anywhere')) {
        return US_PAT.test(loc);
      }
      return true;
    }
  }
  return false;
});"""
        }
    },
    {
        "id": "16",
        "name": "Keyword Prefilter",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [2080, 300],
        "parameters": {
            "jsCode": """const cfg = $('Hunt Config').first().json;
const includes = (cfg.keywords_include || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
const excludes = (cfg.keywords_exclude_title || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);

return $input.all().filter(item => {
  const j = item.json;
  const title = (j.title || '').toLowerCase().trim();
  const desc = (j.description || '').toLowerCase();
  if (!title) return false;

  const hasInc = includes.some(kw => title.includes(kw) || desc.includes(kw));
  if (!hasInc) return false;

  const hasExc = excludes.some(ex => title.includes(ex));
  if (hasExc) {
    const titleHasInc = includes.some(kw => title.includes(kw));
    if (!titleHasInc) return false;
  }
  return true;
});"""
        }
    },
    {
        "id": "17",
        "name": "Drop Already Seen",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [2280, 300],
        "parameters": {
            "jsCode": """// Read Ledger listing_ids and fingerprints to prevent duplicate scoring
const seen_ids = new Set();
const seen_fps = new Set();

try {
  const ledgerRows = $('Read Ledger Sheet').all() || [];
  for (const r of ledgerRows) {
    if (r.json.listing_id) seen_ids.add(r.json.listing_id);
    if (r.json.fingerprint) seen_fps.add(r.json.fingerprint);
  }
} catch (e) {}

const unique = [];
for (const item of $input.all()) {
  const j = item.json;
  if (!seen_ids.has(j.listing_id) && !seen_fps.has(j.fingerprint)) {
    seen_ids.add(j.listing_id);
    seen_fps.add(j.fingerprint);
    unique.push(item);
  }
}
return unique;"""
        }
    },
    {
        "id": "18",
        "name": "New Item?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": [2480, 300],
        "parameters": {
            "conditions": {
                "number": [
                    {"value1": "={{ $input.all().length }}", "operation": "larger", "value2": 0}
                ]
            }
        }
    },
    {
        "id": "19",
        "name": "Nothing New Notice",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [2700, 420],
        "parameters": {
            "chatId": "={{ $('Parse Telegram Command').first().json.chatId || 'DEFAULT_CHAT_ID' }}",
            "text": "Quiet success: No new US listings found today. All matching listings have already been reviewed and logged."
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    {
        "id": "20",
        "name": "Scoring Batch",
        "type": "n8n-nodes-base.splitInBatches",
        "typeVersion": 3,
        "position": [2700, 240],
        "parameters": {
            "batchSize": 5
        }
    },
    {
        "id": "21",
        "name": "Score Listing",
        "type": "@n8n/n8n-nodes-langchain.chainLlm",
        "typeVersion": 1.4,
        "position": [2920, 240],
        "parameters": {
            "prompt": """=LISTING
title: {{ $json.title }}
company: {{ $json.company }}
location: {{ $json.location }} | {{ $json.country }} | remote={{ $json.remote }}
source: {{ $json.source }}  url: {{ $json.url }}  posted_at: {{ $json.posted_at }}
agency_suspect: {{ $json.agency_suspect }}
description:
{{ $json.description ? $json.description.slice(0, 5000) : '' }}"""
        }
    },
    {
        "id": "22",
        "name": "Google Gemini Chat Model (Scoring)",
        "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
        "typeVersion": 1,
        "position": [2920, 420],
        "parameters": {
            "modelName": "models/gemini-2.5-flash"
        },
        "credentials": {"googlePalmApi": {"id": "gemini_cred", "name": "Google Gemini account"}}
    },
    {
        "id": "23",
        "name": "Listing Schema",
        "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
        "typeVersion": 1.1,
        "position": [3100, 420],
        "parameters": {
            "schemaType": "manual",
            "inputSchema": json.dumps({
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["DIRECT_GIG", "BUY_SIGNAL", "IGNORE"]},
                    "score": {"type": "integer"},
                    "band": {"type": "string", "enum": ["low", "medium", "high"]},
                    "one_line_fit": {"type": "string"},
                    "angle": {"type": "string"},
                    "approach_role": {"type": "string"},
                    "asks_for": {"type": "string"},
                    "concern": {"type": "string"},
                    "agency_post": {"type": "boolean"},
                    "keep": {"type": "boolean"}
                },
                "required": ["type", "score", "band", "one_line_fit", "angle", "approach_role", "asks_for", "concern", "agency_post", "keep"]
            })
        }
    },
    {
        "id": "24",
        "name": "Attach Scores",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [3280, 240],
        "parameters": {
            "jsCode": """const parsed = $json.output || {};
const listing = $('Scoring Batch').item.json;
const score = Number(parsed.score || 0);
const type = parsed.type || 'IGNORE';
const keep = (type !== 'IGNORE' && score >= 55);
const band = score >= 80 ? 'high' : (score >= 55 ? 'medium' : 'low');

return [{
  json: {
    ...listing,
    ...parsed,
    score,
    type,
    keep,
    band,
    run_at: new Date().toISOString()
  }
}];"""
        }
    },
    {
        "id": "25",
        "name": "Log To Ledger",
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.3,
        "position": [3480, 240],
        "parameters": {
            "operation": "append",
            "sheetName": "Ledger",
            "documentId": {"__rl": True, "value": "GOOGLE_SPREADSHEET_ID", "mode": "id"}
        },
        "continueOnFail": True,
        "credentials": {"googleSheetsOAuth2": {"id": "sheets_cred", "name": "Google Sheets account"}}
    },
    {
        "id": "26",
        "name": "Keep Relevant",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": [3680, 240],
        "parameters": {
            "conditions": {
                "boolean": [
                    {"value1": "={{ $json.keep }}", "value2": True}
                ]
            }
        }
    },
    {
        "id": "27",
        "name": "Append To Pipeline Sheet",
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.3,
        "position": [3880, 180],
        "parameters": {
            "operation": "appendOrUpdate",
            "sheetName": "Pipeline",
            "documentId": {"__rl": True, "value": "GOOGLE_SPREADSHEET_ID", "mode": "id"},
            "columnToMatchOn": "listing_id"
        },
        "continueOnFail": True,
        "credentials": {"googleSheetsOAuth2": {"id": "sheets_cred", "name": "Google Sheets account"}}
    },
    {
        "id": "28",
        "name": "Hot Only",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": [4080, 180],
        "parameters": {
            "conditions": {
                "number": [
                    {"value1": "={{ $json.score }}", "operation": "largerEqual", "value2": 80}
                ]
            }
        }
    },
    {
        "id": "29",
        "name": "Telegram Hot Alert",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [4280, 120],
        "parameters": {
            "chatId": "={{ $('Parse Telegram Command').first().json.chatId || 'DEFAULT_CHAT_ID' }}",
            "text": """={{ ($json.agency_post ? "POSTED VIA AGENCY - the real employer is hidden\\n" : "") + "**" + $json.type + "** — score " + $json.score + " (" + $json.band + ")\\n**" + $json.title + "**\\n" + $json.company + " | " + ($json.location || "US Remote") + " | " + ($json.country || "US") + " | " + $json.source + "\\n\\n" + $json.one_line_fit + "\\n\\n**Angle:** " + $json.angle + "\\n**Approach:** " + $json.approach_role + "\\n**Asks for:** " + $json.asks_for + "\\n**Concern:** " + $json.concern }}""",
            "replyMarkup": "inlineKeyboard",
            "inlineKeyboard": {
                "rows": [
                    {
                        "row": {
                            "buttons": [
                                {"text": "✍️ Draft outreach", "additionalFields": {"callback_data": "=draft::{{ $json.listing_id }}"}},
                                {"text": "🔗 Open posting", "additionalFields": {"callback_data": "=open::{{ $json.listing_id }}"}}
                            ]
                        }
                    },
                    {
                        "row": {
                            "buttons": [
                                {"text": "🔎 Find contact", "additionalFields": {"callback_data": "=contact::{{ $json.listing_id }}"}}
                            ]
                        }
                    }
                ]
            }
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    {
        "id": "30",
        "name": "Build Digest",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [4480, 240],
        "parameters": {
            "jsCode": """const now = new Date().toISOString();
const allScored = $('Attach Scores').all() || [];
const kept = allScored.filter(i => i.json.keep).length;
const hot = allScored.filter(i => i.json.score >= 80).length;
const total = allScored.length;

return [{
  json: {
    digest_text: `Auto Bot digest — ${now}\\nScored: ${total}   Kept: ${kept}   Hot: ${hot}`
  }
}];"""
        }
    },
    {
        "id": "31",
        "name": "Send Run Report",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [4680, 240],
        "parameters": {
            "chatId": "={{ $('Parse Telegram Command').first().json.chatId || 'DEFAULT_CHAT_ID' }}",
            "text": "={{ $json.digest_text }}"
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    # Act path nodes
    {
        "id": "32",
        "name": "Acknowledge Button",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [780, 800],
        "parameters": {
            "operation": "answerCallbackQuery",
            "callbackQueryId": "={{ $json.callback_id }}"
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    {
        "id": "33",
        "name": "Lookup Listing",
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.3,
        "position": [1000, 800],
        "parameters": {
            "operation": "lookup",
            "sheetName": "Pipeline",
            "documentId": {"__rl": True, "value": "GOOGLE_SPREADSHEET_ID", "mode": "id"},
            "lookupColumn": "listing_id",
            "lookupValue": "={{ $('Parse Telegram Command').first().json.listing_id }}"
        },
        "credentials": {"googleSheetsOAuth2": {"id": "sheets_cred", "name": "Google Sheets account"}}
    },
    {
        "id": "34",
        "name": "Evaluate Cooldown",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1220, 800],
        "parameters": {
            "jsCode": """const days = Number($('Hunt Config').first().json.cooldown_days || 21);
const last = $json.last_touch_at ? new Date($json.last_touch_at) : null;
const blocked = last && (Date.now() - last.getTime()) / 86400000 < days;
return [{ json: { ...$json, cooldown: blocked ? 'blocked' : 'allowed' } }];"""
        }
    },
    {
        "id": "35",
        "name": "Cooldown Gate",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": [1440, 800],
        "parameters": {
            "conditions": {
                "string": [
                    {"value1": "={{ $json.cooldown }}", "operation": "equals", "value2": "allowed"}
                ]
            }
        }
    },
    {
        "id": "36",
        "name": "Telegram Cooldown Notice",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [1660, 920],
        "parameters": {
            "chatId": "={{ $('Parse Telegram Command').first().json.chatId }}",
            "text": "=⏸️ Cooldown Notice: A draft was created for {{ $json.company }} within the last 21 days. Blocked."
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    {
        "id": "37",
        "name": "Draft Outreach",
        "type": "@n8n/n8n-nodes-langchain.chainLlm",
        "typeVersion": 1.4,
        "position": [1660, 780],
        "parameters": {
            "prompt": """=Write a short note the operator can paste into LinkedIn or email.
Do not send anything. Do not invent meetings, metrics, or case studies.
Use at most ONE proof point from the list, or none if none fit.
Do not dump the resume.
BUY_SIGNAL: write to {{ $json.approach_role }}. Treat the hire as proof of intent.
Position hands-on experience designing, developing, and deploying production GenAI systems, autonomous agent workflows, and RAG architectures in Python, TypeScript, and GCP.
DIRECT_GIG: write as a specialist proposing to deliver rapid AI prototyping and API deployment.
80-130 words. Plain text.

CARD:
{{ $json.type }} {{ $json.score }} {{ $json.title }} @ {{ $json.company }}
Fit: {{ $json.one_line_fit }}
Angle: {{ $json.angle }}
Concern: {{ $json.concern }}"""
        }
    },
    {
        "id": "38",
        "name": "Google Gemini Chat Model",
        "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
        "typeVersion": 1,
        "position": [1660, 980],
        "parameters": {
            "modelName": "models/gemini-2.5-flash"
        },
        "credentials": {"googlePalmApi": {"id": "gemini_cred", "name": "Google Gemini account"}}
    },
    {
        "id": "39",
        "name": "Send Draft",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [1880, 780],
        "parameters": {
            "chatId": "={{ $('Parse Telegram Command').first().json.chatId }}",
            "text": "=📝 Outreach Draft for {{ $('Lookup Listing').first().json.company }}:\\n\\n{{ $json.response }}"
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    },
    {
        "id": "40",
        "name": "Find Contact",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1000, 1100],
        "parameters": {
            "jsCode": """const q = encodeURIComponent(($json.approach_role || 'VP of Engineering / Head of AI') + ' ' + ($json.company || ''));
return [{ json: { ...$json, contact_url: 'https://www.linkedin.com/search/results/people/?keywords=' + q } }];"""
        }
    },
    {
        "id": "41",
        "name": "Telegram Contact Result",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [1220, 1100],
        "parameters": {
            "chatId": "={{ $('Parse Telegram Command').first().json.chatId }}",
            "text": "=🔎 LinkedIn People Search for {{ $json.company }}:\\n<{{ $json.contact_url }}>"
        },
        "credentials": {"telegramApi": {"id": "telegram_cred", "name": "Telegram account"}}
    }
]

connections = {
    "Daily Hunt": {"main": [[{"node": "Hunt Config", "type": "main", "index": 0}]]},
    "Telegram Command": {"main": [[{"node": "Parse Telegram Command", "type": "main", "index": 0}]]},
    "Parse Telegram Command": {"main": [[{"node": "Route Command", "type": "main", "index": 0}]]},
    "Route Command": {
        "main": [
            [{"node": "Hunt Config", "type": "main", "index": 0}],      # 0: hunt
            [],                                                         # 1: status
            [{"node": "Telegram Help", "type": "main", "index": 0}],    # 2: help
            [{"node": "Acknowledge Button", "type": "main", "index": 0}],# 3: draft
            [{"node": "Acknowledge Button", "type": "main", "index": 0}],# 4: open
            [{"node": "Acknowledge Button", "type": "main", "index": 0}] # 5: contact
        ]
    },
    "Hunt Config": {
        "main": [
            [
                {"node": "Build JobsPipe Payload", "type": "main", "index": 0},
                {"node": "Remotive Feed", "type": "main", "index": 0},
                {"node": "RemoteOK Feed", "type": "main", "index": 0},
                {"node": "Arbeitnow Feed", "type": "main", "index": 0},
                {"node": "Jobicy Feed", "type": "main", "index": 0}
            ]
        ]
    },
    "Build JobsPipe Payload": {"main": [[{"node": "JobsPipe Search", "type": "main", "index": 0}]]},
    "JobsPipe Search": {"main": [[{"node": "Merge All Sources", "type": "main", "index": 0}]]},
    "Remotive Feed": {"main": [[{"node": "Merge All Sources", "type": "main", "index": 0}]]},
    "RemoteOK Feed": {"main": [[{"node": "Merge All Sources", "type": "main", "index": 0}]]},
    "Arbeitnow Feed": {"main": [[{"node": "Merge All Sources", "type": "main", "index": 0}]]},
    "Jobicy Feed": {"main": [[{"node": "Merge All Sources", "type": "main", "index": 0}]]},
    "Merge All Sources": {"main": [[{"node": "Normalize Listings", "type": "main", "index": 0}]]},
    "Normalize Listings": {"main": [[{"node": "Drop Non-US", "type": "main", "index": 0}]]},
    "Drop Non-US": {"main": [[{"node": "Keyword Prefilter", "type": "main", "index": 0}]]},
    "Keyword Prefilter": {"main": [[{"node": "Drop Already Seen", "type": "main", "index": 0}]]},
    "Drop Already Seen": {"main": [[{"node": "New Item?", "type": "main", "index": 0}]]},
    "New Item?": {
        "main": [
            [{"node": "Scoring Batch", "type": "main", "index": 0}],
            [{"node": "Nothing New Notice", "type": "main", "index": 0}]
        ]
    },
    "Scoring Batch": {"main": [[{"node": "Score Listing", "type": "main", "index": 0}]]},
    "Google Gemini Chat Model (Scoring)": {"ai_languageModel": [[{"node": "Score Listing", "type": "ai_languageModel", "index": 0}]]},
    "Listing Schema": {"ai_outputParser": [[{"node": "Score Listing", "type": "ai_outputParser", "index": 0}]]},
    "Score Listing": {"main": [[{"node": "Attach Scores", "type": "main", "index": 0}]]},
    "Attach Scores": {"main": [[{"node": "Log To Ledger", "type": "main", "index": 0}]]},
    "Log To Ledger": {"main": [[{"node": "Keep Relevant", "type": "main", "index": 0}]]},
    "Keep Relevant": {"main": [[{"node": "Append To Pipeline Sheet", "type": "main", "index": 0}]]},
    "Append To Pipeline Sheet": {"main": [[{"node": "Hot Only", "type": "main", "index": 0}]]},
    "Hot Only": {
        "main": [
            [{"node": "Telegram Hot Alert", "type": "main", "index": 0}],
            [{"node": "Build Digest", "type": "main", "index": 0}]
        ]
    },
    "Telegram Hot Alert": {"main": [[{"node": "Build Digest", "type": "main", "index": 0}]]},
    "Build Digest": {"main": [[{"node": "Send Run Report", "type": "main", "index": 0}]]},
    "Acknowledge Button": {"main": [[{"node": "Lookup Listing", "type": "main", "index": 0}]]},
    "Lookup Listing": {"main": [[{"node": "Evaluate Cooldown", "type": "main", "index": 0}]]},
    "Evaluate Cooldown": {"main": [[{"node": "Cooldown Gate", "type": "main", "index": 0}]]},
    "Cooldown Gate": {
        "main": [
            [{"node": "Draft Outreach", "type": "main", "index": 0}],
            [{"node": "Telegram Cooldown Notice", "type": "main", "index": 0}]
        ]
    },
    "Google Gemini Chat Model": {"ai_languageModel": [[{"node": "Draft Outreach", "type": "ai_languageModel", "index": 0}]]},
    "Draft Outreach": {"main": [[{"node": "Send Draft", "type": "main", "index": 0}]]},
    "Find Contact": {"main": [[{"node": "Telegram Contact Result", "type": "main", "index": 0}]]}
}

workflow = {
    "name": "Auto Bot LinkedIn Job",
    "nodes": nodes,
    "connections": connections,
    "active": False,
    "settings": {"executionOrder": "v1"},
    "tags": []
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(workflow, f, indent=2)

print(f"Generated n8n workflow at {OUTPUT_FILE}")
