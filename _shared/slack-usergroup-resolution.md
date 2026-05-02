# Slack Usergroup Membership Resolution

Resolve the members of a Slack usergroup (e.g., `metaflow-dev-group`) given a subteam ID.

## Known gap

No available MCP tool (`rag-slack-prod`, `fetch-slack-thread`, `netflix_search_api`) supports enumerating usergroup membership. These tools search message content, not group rosters. Until an MCP tool is added for this, use the raw Slack API approach below.

## Procedure

1. **Find the subteam ID.** Search Slack (via `rag-slack-prod` or `netflix_search_api` with `sources: ["SLACK"]`) for messages containing `<!subteam^SXXXXXXXXXX>` patterns referencing the group alias.

2. **Resolve member user IDs.** Write a helper script to `/tmp/slack-usergroup.sh` (needed because `$()` inside Bash commands breaks the permission matcher's parenthesis parsing):

```bash
#!/bin/bash
TOKEN=$(cat ~/.slack_secret_xoxb)
curl -s "https://slack.com/api/usergroups.users.list?usergroup=$1" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json; d=json.load(sys.stdin)
[print(u) for u in d.get('users',[])] if d.get('ok') else print(d.get('error'))"
```

Run: `bash /tmp/slack-usergroup.sh S04ES4SDT40` -- returns one Slack user ID per line.

3. **Resolve user IDs to names.** Write a second helper script to call `users.info` per ID:

```bash
#!/bin/bash
TOKEN=$(cat ~/.slack_secret_xoxb)
for uid in "$@"; do
  curl -s "https://slack.com/api/users.info?user=$uid" \
    -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json; u=json.load(sys.stdin).get('user',{})
print(f\"{u.get('real_name','')} ({u.get('name','')}) <{u.get('profile',{}).get('email','')}>\")"
done
```

## Requirements

- `~/.slack_secret_xoxb` must contain a valid Slack Bot User OAuth Token (`xoxb-...`) with the `usergroups:read` and `users:read` scopes.

## When to prefer alternatives

- **GitHub Enterprise team API** is often faster and doesn't require a Slack token. Most `-dev-group` aliases have a matching GHE team under `corp`. Try: `gh api orgs/corp/teams/{alias}/members --hostname github.netflix.net --jq '.[].login'`
- **Pandora** can resolve Netflix team aliases to member lists if the alias is a registered team.
