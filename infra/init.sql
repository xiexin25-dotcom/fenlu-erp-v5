-- 4 个 lane 的 schema 隔离 + 1 个 public 给 foundation
CREATE SCHEMA IF NOT EXISTS plm;   -- Lane 1 product lifecycle
CREATE SCHEMA IF NOT EXISTS mfg;   -- Lane 2 production
CREATE SCHEMA IF NOT EXISTS scm;   -- Lane 3 supply chain
CREATE SCHEMA IF NOT EXISTS mgmt;  -- Lane 4 management decision

GRANT ALL ON SCHEMA plm, mfg, scm, mgmt TO fenlu;
