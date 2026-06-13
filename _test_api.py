# -*- coding: utf-8 -*-
"""Quick API test"""
import http.client, json

conn = http.client.HTTPConnection('localhost', 8701)
body = json.dumps({"content": "\u4eca\u5929\u8bfb\u4e86\u6751\u4e0a\u6625\u6811\u7684\u5c0f\u8bf4\uff0c\u611f\u89c9\u5f88\u653e\u677e", "source": "text"}).encode('utf-8')
conn.request('POST', '/memories', body=body, headers={'Content-Type': 'application/json; charset=utf-8'})
resp = conn.getresponse()
data = json.loads(resp.read().decode('utf-8'))
print("OK: id=%s" % data["id"])
print("content: %s" % data["content"])
print("tags: %s" % data["tags"])
print("summary: %s" % data.get("summary", ""))

# Also test search
conn2 = http.client.HTTPConnection('localhost', 8701)
conn2.request('GET', '/memories/search?q=%E5%B0%8F%E8%AF%B4&mode=keyword')
resp2 = conn2.getresponse()
data2 = json.loads(resp2.read().decode('utf-8'))
print("\nSearch 'xiaoshuo': %d results" % len(data2))
for r in data2:
    mem = r.get("memory", r)
    print("  - [%s] %s (score=%.3f)" % (mem["id"], mem["content"][:40], r.get("score", 0)))

# Stats
conn3 = http.client.HTTPConnection('localhost', 8701)
conn3.request('GET', '/stats')
resp3 = conn3.getresponse()
data3 = json.loads(resp3.read().decode('utf-8'))
print("\nStats: %d mems, %d tags" % (data3["total_memories"], data3["total_tags"]))
