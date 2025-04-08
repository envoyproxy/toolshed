import argparse
import asyncio
import base64
import collections
import hashlib
import json
import os
import pathlib
import re
import signal
import sys
import tempfile
import time
from functools import cached_property

from mcp.server.fastmcp import Context, Image, FastMCP
from mcp.server.fastmcp.prompts import base
import sqlite3

mcp = FastMCP("Me")

ALLOWED_POLICIES = {"MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "MAY"}


class MyContext:
    def __init__(self, db):
        self._db = db

    @cached_property
    def db(self):
        return self.create_db()

    @property
    def db_path(self):
        return pathlib.Path(self._db)

    def close(self):
        self.db.close()

    def create_db(self):
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules (
        policy TEXT CHECK(policy IN ('MUST', 'MUST NOT', 'SHOULD', 'SHOULD NOT', 'MAY')),
        rule TEXT,
        context TEXT,
        UNIQUE(rule, context)
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artefacts (
            type TEXT,
            context TEXT,
            key TEXT,
            artefact TEXT,
            UNIQUE(key, context)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            type TEXT,
            context TEXT,
            key TEXT,
            snippet TEXT,
            UNIQUE(key, context)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            type TEXT,
            context TEXT,
            key TEXT,
            summary TEXT,
            UNIQUE(key, context)
        )
        """)
        return conn

    def get(self, context=None):
        cursor = self.db.cursor()

        if context is None:
            cursor.execute("SELECT * FROM rules WHERE context IS NULL")
        else:
            cursor.execute("SELECT * FROM rules WHERE context = ?", (context,))

        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        return [dict(zip(column_names, row)) for row in rows]

    def get_artefact(self, context, key):
        cursor = self.db.cursor()
        cursor.execute("SELECT artefact FROM artefacts WHERE key = ? AND context = ?", (key, context))
        artefact = cursor.fetchone()
        return artefact and artefact[0]

    def get_rule(self, rule, context=None):
        cursor = self.db.cursor()
        if context is None:
            cursor.execute("SELECT policy FROM rules WHERE rule = ? AND context IS NULL", (rule,))
        else:
            cursor.execute("SELECT policy FROM rules WHERE rule = ? AND context = ?", (rule, context))
        return cursor.fetchone()

    def get_snippet(self, context, key):
        cursor = self.db.cursor()
        cursor.execute("SELECT snippet FROM snippets WHERE key = ? AND context = ?", (key, context))
        snippet = cursor.fetchone()
        return snippet and snippet[0]

    def get_summary(self, context, key):
        cursor = self.db.cursor()
        cursor.execute("SELECT summary FROM summaries WHERE key = ? AND context = ?", (key, context))
        summary = cursor.fetchone()
        return summary and summary[0]

    def list_snippets(self, context):
        cursor = self.db.cursor()
        cursor.execute("SELECT snippet FROM snippets WHERE context = ?", (context, ))
        return cursor.fetchall()

    def list_summaries(self, context):
        cursor = self.db.cursor()
        cursor.execute("SELECT summary FROM summaries WHERE context = ?", (context, ))
        return cursor.fetchall()

    def remove_rule(self, rule, context=None):
        cursor = self.db.cursor()
        if context is None:
            cursor.execute("SELECT policy FROM rules WHERE rule = ? AND context IS NULL", (rule,))
        else:
            cursor.execute("SELECT policy FROM rules WHERE rule = ? AND context = ?", (rule, context))
        result = cursor.fetchone()
        if result:
            if context is None:
                cursor.execute("DELETE FROM rules WHERE rule = ? AND context IS NULL", (rule,))
            else:
                cursor.execute("DELETE FROM rules WHERE rule = ? AND context = ?", (rule, context))
            self.db.commit()
            return json.dumps({
                "status": "ok",
                "message": f"Rule '{rule}' removed successfully"
            })
        return json.dumps({
            "error": f"Rule '{rule}' not found with the specified context"
        })

    def set_artefact(self, context, type_name, key, artefact):
        cursor = self.db.cursor()
        cursor.execute("SELECT type FROM artefacts WHERE key = ? AND context IS ?", (key, context))
        row = cursor.fetchone()
        if row:
            existing_type = row[0]
            if existing_type == type_name:
                return json.dumps({
                    "error": "Artefact already exists with the same key, type and context"
                })
            cursor.execute("UPDATE artefacts SET type = ? WHERE key = ? AND context IS ?", (type_nane, key, context))
            self.db.commit()
            return json.dumps({
                "status": "ok",
                "message": f"Type updated from '{existing_type}' to '{type_name}'"
            })
        cursor.execute("INSERT INTO artefacts (type, key, artefact, context) VALUES (?, ?, ?, ?)", (type_name, key, artefact, context))
        self.db.commit()
        return json.dumps({
            "status": "ok",
            "message": "New artefact added"
        })

    def set_rule(self, policy, rule, context=None):
        if policy not in ALLOWED_POLICIES:
            return json.dumps({
                "error": f"Invalid policy '{policy}'. Must be one of: {sorted(ALLOWED_POLICIES)}"
            })
        cursor = self.db.cursor()
        cursor.execute("SELECT policy FROM rules WHERE rule = ? AND context IS ?", (rule, context))
        row = cursor.fetchone()
        if row:
            existing_policy = row[0]
            if existing_policy == policy:
                return json.dumps({
                    "error": "Rule already exists with the same policy and context"
                })
            cursor.execute("UPDATE rules SET policy = ? WHERE rule = ? AND context IS ?", (policy, rule, context))
            self.db.commit()
            return json.dumps({
                "status": "ok",
                "message": f"Policy updated from '{existing_policy}' to '{policy}'"
            })
        cursor.execute("INSERT INTO rules (policy, rule, context) VALUES (?, ?, ?)", (policy, rule, context))
        self.db.commit()
        return json.dumps({
            "status": "ok",
            "message": "New rule added"
        })

    def set_snippet(self, context, type_name, key, snippet):
        cursor = self.db.cursor()
        cursor.execute("SELECT type FROM snippets WHERE key = ? AND context IS ?", (key, context))
        row = cursor.fetchone()
        if row:
            existing_type = row[0]
            if existing_type == type_name:
                return json.dumps({
                    "error": "Snippet already exists with the same key, type and context"
                })
            cursor.execute("UPDATE snippets SET type = ? WHERE key = ? AND context IS ?", (type_nane, key, context))
            self.db.commit()
            return json.dumps({
                "status": "ok",
                "message": f"Type updated from '{existing_type}' to '{type_name}'"
            })
        cursor.execute("INSERT INTO snippets (type, key, snippet, context) VALUES (?, ?, ?, ?)", (type_name, key, snippet, context))
        self.db.commit()
        return json.dumps({
            "status": "ok",
            "message": "New snippet added"
        })

    def set_summary(self, context, type_name, key, summary):
        cursor = self.db.cursor()
        cursor.execute("SELECT type FROM summaries WHERE key = ? AND context IS ?", (key, context))
        row = cursor.fetchone()
        if row:
            existing_type = row[0]
            if existing_type == type_name:
                return json.dumps({
                    "error": "Summary already exists with the same key, type and context"
                })
            cursor.execute("UPDATE summaries SET type = ? WHERE key = ? AND context IS ?", (type_nane, key, context))
            self.db.commit()
            return json.dumps({
                "status": "ok",
                "message": f"Type updated from '{existing_type}' to '{type_name}'"
            })
        cursor.execute("INSERT INTO summaries (type, key, summary, context) VALUES (?, ?, ?, ?)", (type_name, key, summary, context))
        self.db.commit()
        return json.dumps({
            "status": "ok",
            "message": "New summary added"
        })


# RESOURCES

@mcp.resource("my-context://{namespace}")
async def my_context_resource(namespace: str) -> str:
    """My context"""
    me = MyContext("/tmp/me/my.db")
    data = me.get(context=(namespace if namespace != "me" else None))
    me.close()
    json_output = json.dumps(data, indent=4)
    return json_output


# TOOLS

@mcp.tool()
async def my_context(ctx: Context, extra_context: list[str] | None = None) -> str:
    """Context for working with me

    This MUST always be loaded when working with me.
    """
    context = await ctx.read_resource(f"my-context://me")
    for extra in (extra_context or []):
        context += await ctx.read_resource(f"my-context://{extra}")
    return context


@mcp.tool()
async def my_context_get_artefact(context: str, key: str, ctx: Context) -> Image:
    """Get context artefact for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.get_artefact(context, key)
    result = base64.b64decode(result)
    me.close()
    pathlib.Path("/tmp/foo.jpg").write_bytes(result)
    result = Image(data=result, format="image/png")
    return result


@mcp.tool()
async def my_context_get_snippet(context: str, key: str, ctx: Context) -> str:
    """Get context snippet for working with me"""
    me = MyContext("/tmp/me/my.db")
    return me.get_snippet(context, key)


@mcp.tool()
async def my_context_set_snippet(type_name: str, key: str, snippet: bytes, ctx: Context, context: str) -> str:
    """Set context snippet for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.set_snippet(context, type_name, key, snippet)
    me.close()
    return result


@mcp.tool()
async def my_context_set_summary(type_name: str, key: str, summary: bytes, ctx: Context, context: str) -> str:
    """Set context summary for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.set_summary(context, type_name, key, summary)
    me.close()
    return result


@mcp.tool()
async def my_context_list_snippets(context: str, ctx: Context) -> str:
    """List context snippets for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.list_snippets(context)
    me.close()
    return result


@mcp.tool()
async def my_context_list_summary(context: str, ctx: Context) -> str:
    """List context summaries for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.list_summaries(context)
    me.close()
    return result


@mcp.tool()
async def my_context_set_artefact(type_name: str, key: str, artefact: bytes, ctx: Context, context: str) -> str:
    """Set context artefact for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.set_artefact(context, type_name, key, artefact)
    me.close()
    return result


@mcp.tool()
async def set_my_context_rule(policy: str, rule: str, ctx: Context, context: str = None) -> str:
    """Set context for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.set_rule(policy, rule, context)
    me.close()
    return result


@mcp.tool()
async def remove_my_context_rule(rule: bytes, ctx: Context, context: str = None) -> str:
    """Remove context for working with me"""
    me = MyContext("/tmp/me/my.db")
    result = me.remove_rule(rule, context)
    me.close()
    return result


# PROMPTS

@mcp.prompt()
def my_prompt() -> str:
    """Create my prompt"""
    current_file = pathlib.Path(__file__)
    context_file_path = current_file.parent / "prompt.txt"
    return context_file_path.read_text()
