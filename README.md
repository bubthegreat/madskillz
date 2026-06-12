# madskillz

Personal Claude Code marketplace: skills, plugins, and global rules, versioned in one place.

## Layout

```
madskillz/
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest, lists plugins
├── plugins/
│   └── madskillz/                # single bundle plugin (split later if needed)
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
│           └── uv/               # Python packaging via uv
├── rules/
│   └── global.md                 # always-loaded rules, imported by ~/.claude/CLAUDE.md
└── README.md
```

When the plugin grows commands, agents, or hooks, they go in
`plugins/madskillz/commands/`, `plugins/madskillz/agents/`, and
`plugins/madskillz/hooks/` respectively — create the directories when first needed.

## Bootstrap (any machine)

```
/plugin marketplace add bubthegreat/madskillz
/plugin install madskillz@madskillz
```

Then make `~/.claude/CLAUDE.md` import the global rules:

```
@/path/to/madskillz/rules/global.md
```

## Iterating

Plugin installs are cached copies — edits don't take effect until the cache updates:

1. Edit locally
2. `git push`
3. `/plugin marketplace update madskillz`

Rules in `rules/global.md` need no update step on this machine: the `@` import in
`~/.claude/CLAUDE.md` reads the working copy directly each session.

## Where does new stuff go?

| It is... | Put it in... |
|---|---|
| A rule Claude should always follow (one or two lines) | `rules/global.md` |
| A procedure or reference Claude needs on demand | a skill in `plugins/madskillz/skills/` |
| Something that must mechanically happen (not rely on Claude remembering) | a hook in `plugins/madskillz/hooks/` |

Pattern: keep the always-rule short and point it at the skill that holds the detail,
e.g. "Python packaging: always uv, never pip — details in uv skill."
