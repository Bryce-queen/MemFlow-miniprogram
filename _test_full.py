# -*- coding: utf-8 -*-
import json, urllib.request, ssl

ctx = ssl._create_unverified_context()

# Test 1: List memories
req = urllib.request.Request('http://localhost:8701/memories?limit=3')
resp = urllib.request.urlopen(req, context=ctx)
data = json.loads(resp.read().decode('utf-8'))
print('Test 1 - GET /memories:')
print('  count=%d' % len(data))
for m in data:
    print('  [%s] tags=%s summary=%s content_len=%d' % (
        m['id'], len(m.get('tags', [])), bool(m.get('summary')), len(m.get('content', ''))
    ))

# Test 2: Search memory
srch = urllib.parse.quote('小说', encoding='utf-8')
req2 = urllib.request.Request('http://localhost:8701/memories/search?q=%s&mode=keyword' % srch)
resp2 = urllib.request.urlopen(req2, context=ctx)
data2 = json.loads(resp2.read().decode('utf-8'))
print('\nTest 2 - GET /memories/search?q=小说:')
print('  results=%d' % len(data2))

# Test 3: Health
req3 = urllib.request.Request('http://localhost:8701/health')
resp3 = urllib.request.urlopen(req3, context=ctx)
data3 = json.loads(resp3.read().decode('utf-8'))
print('\nTest 3 - GET /health:')
print('  status=%s mems=%d AI=%s' % (data3['status'], data3['total_memories'], data3['ai_available']))

# Test 4: Stats
req4 = urllib.request.Request('http://localhost:8701/stats')
resp4 = urllib.request.urlopen(req4, context=ctx)
data4 = json.loads(resp4.read().decode('utf-8'))
print('\nTest 4 - GET /stats:')
print('  total=%d tags=%d recent_7d=%d' % (data4['total_memories'], data4['total_tags'], data4['recent_count_7d']))

# Test 5: Create memory properly
import http.client
conn = http.client.HTTPConnection('localhost', 8701)
payload = json.dumps({"content": "\u4eca\u5929\u53bb\u4e86\u65b0\u4e66\u5e97\u901b\u4e86\u4e00\u4e0b\u5348\uff0c\u4e70\u4e86\u4e09\u672c\u8ba1\u7b97\u673a\u4e66\u7c4d", "source": "text"})
conn.request('POST', '/memories', body=payload.encode('utf-8'), headers={'Content-Type': 'application/json; charset=utf-8'})
resp5 = conn.getresponse()
data5 = json.loads(resp5.read().decode('utf-8'))
print('\nTest 5 - POST /memories (create):')
print('  id=%s tags_count=%d summary_len=%d' % (data5['id'], len(data5.get('tags', [])), len(data5.get('summary', ''))))

# Test 6: Search again
req6 = urllib.request.Request('http://localhost:8701/memories/search?q=%s&mode=keyword' % urllib.parse.quote('计算机', encoding='utf-8'))
resp6 = urllib.request.urlopen(req6, context=ctx)
data6 = json.loads(resp6.read().decode('utf-8'))
print('\nTest 6 - Search for jisuanji:')
print('  results=%d' % len(data6))

print('\n=== ALL TESTS PASSED ===')
