CREATE TABLE IF NOT EXISTS actions (
    "action_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "action_time" TEXT,
    "action" TEXT,
    "author" TEXT,
    "author_id" TEXT,
    "channel" TEXT,
    "channel_id" TEXT,
    "guild" TEXT,
    "guild_id" TEXT
);

CREATE TABLE IF NOT EXISTS voteables (
    "action_id" int REFERENCES actions("action_id") ON DELETE CASCADE,
    "phrase" TEXT,
    "vote" TEXT
);