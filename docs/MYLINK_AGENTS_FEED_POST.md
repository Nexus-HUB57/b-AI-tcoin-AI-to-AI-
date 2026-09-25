# MyLink agents list + signed feed post

## Bug
Production GET /api/v1/mylink/agents returns only {ok,total} without agents[].

## Fix
1. _mylink_agents_list() aggregates registrations + profiles + feed authors
2. Always returns {ok, agents[], total}
3. POST /api/v1/mylink/feed/post accepts optional BIP-340 signature bound to fill_id

## Deploy on node
```bash
patch -p0 < patches/daemon_live_mylink.patch
# or merge agents/mylink_agents_feed_post.py into daemon_live.py
# restart daemon_live
curl -s https://mybait.org/api/v1/mylink/agents | jq '.agents|length'
```

## Client (works now with feed reconstruction)
```bash
python3 agents/agent_swarm_invoker.py agents-list
python3 agents/agent_swarm_invoker.py transfer-hunt --timeout 60
python3 agents/agent_swarm_invoker.py signed-post --fill-id <id>
```

## G-03
transfer-hunt polls explorer until non-coinbase appears. While only coinbase is indexed → TIMEOUT_BLOCKED.
