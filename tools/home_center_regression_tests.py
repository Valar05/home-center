#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
failures = []

def read(relative):
    return (ROOT / relative).read_text()

def fail(message):
    failures.append(message)

def method_body(source, signature, next_signature):
    start = source.find(signature)
    if start < 0:
        fail(f"missing method signature: {signature}")
        return ""
    end = source.find(next_signature, start + len(signature))
    if end < 0:
        fail(f"missing following method signature: {next_signature}")
        return source[start:]
    return source[start:end]

def require_before(body, first, second, label):
    left = body.find(first)
    right = body.find(second)
    if left < 0:
        fail(f"{label}: missing {first}")
    if right < 0:
        fail(f"{label}: missing {second}")
    if left >= 0 and right >= 0 and left > right:
        fail(f"{label}: {first} must appear before {second}")

def require_contains(source, needle, label):
    if needle not in source:
        fail(f"{label}: missing {needle}")

home = read('app/src/main/java/com/dclar/homecenter/HomeTaskClient.java')
add_task = method_body(home, 'void addTask(', 'void loadActiveTasks(')
load_tasks = method_body(home, 'void loadActiveTasks(', 'void markDone(')
mark_done = method_body(home, 'void markDone(', 'void removeTaskByName(')
remove_task = method_body(home, 'void removeTaskByName(', 'private ListResult toListResult(')
create_list = method_body(home, 'void createList(', 'void addTask(')
join = method_body(home, 'void joinHousehold(', 'void createList(')

require_before(add_task, 'ensureListForAccess', 'listRef.collection("tasks").add(task)', 'addTask list guard before task create')
require_before(load_tasks, 'ensureListForAccess', 'whereEqualTo("status", "active")', 'loadActiveTasks list guard before task query')
require_before(mark_done, 'ensureListForAccess', 'document(task.id).set(update, SetOptions.merge())', 'markDone list guard before task update')
require_before(remove_task, 'ensureListForAccess', 'whereEqualTo("status", "active")', 'removeTaskByName list guard before task query')
require_before(create_list, 'ensureHouseholdMembership', 'listRef.set(list, SetOptions.merge())', 'createList membership before list write')
require_contains(join, 'ensureHouseholdMembership', 'joinHousehold uses shared membership helper')
require_contains(home, 'private Task<Void> ensureListForAccess', 'shared list access helper exists')
require_contains(home, 'private Task<Void> ensureHouseholdMembership', 'shared membership helper exists')
require_contains(home, 'householdRef.collection("members").document(user.getUid()).set(member, SetOptions.merge())', 'membership helper writes current user member doc')

log = read('app/src/main/java/com/dclar/homecenter/LocalLog.java')
require_contains(log, 'Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/logs/"', 'public local log folder')
require_contains(log, 'MediaStore.Downloads.EXTERNAL_CONTENT_URI', 'logs use Downloads provider')
require_contains(log, 'openOutputStream(uri, "wa")', 'logs append instead of overwrite')

rules = read('firebase/firestore.rules')
require_contains(rules, 'match /members/{uid}', 'rules contain household members')
require_contains(rules, 'allow create, update: if signedIn() && uid == request.auth.uid', 'rules allow self membership')
require_contains(rules, 'allow read, create, update: if isMember(bucketId)', 'rules gate task writes by household membership')

parser = read('app/src/main/java/com/dclar/homecenter/CommandParser.java')
require_contains(parser, 'lower.equals("groceries")', 'parser maps groceries to shopping')
require_contains(parser, 'lower.replaceFirst("\\\\s+(list|lists)$", "")', 'parser strips trailing list')

if failures:
    print('Home Center regression tests failed:', file=sys.stderr)
    for item in failures:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Home Center source-contract tests: OK')
