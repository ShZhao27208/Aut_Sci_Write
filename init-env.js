#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const ROOT_DIR = path.dirname(__filename);
const SKILLS_DIR = path.join(ROOT_DIR, 'skills');

export const SKILL_ENV_SPEC = {
  'sci-search': {
    description: 'Literature search: Web of Science, PubMed/NCBI, and optional Zotero handoff.',
    vars: {
      WOS_API_KEY: 'Web of Science Starter API key. Optional; enables WoS search.',
      NCBI_API_KEY: 'NCBI E-utilities API key. Optional; increases PubMed rate limits.',
      NCBI_EMAIL: 'Contact email sent to NCBI E-utilities. Optional but recommended by NCBI.',
      NCBI_TOOL: 'NCBI tool name. Optional; defaults to sci-search.',
      ZOTERO_API_KEY: 'Zotero API key. Optional; shared with sci-zotero if configured.',
      ZOTERO_USER_ID: 'Zotero personal library user ID. Optional; shared with sci-zotero if configured.'
    }
  },
  'sci-zotero': {
    description: 'Zotero library integration.',
    vars: {
      ZOTERO_API_KEY: 'Zotero API key. Required for Zotero operations.',
      ZOTERO_USER_ID: 'Zotero personal library user ID. Use this or ZOTERO_GROUP_ID.',
      ZOTERO_GROUP_ID: 'Zotero group library ID. Use this or ZOTERO_USER_ID.'
    }
  },
  'sci-ppt': {
    description: 'Academic PPT generation with optional AI parsing and translation.',
    vars: {
      MOONSHOT_API_KEY: 'Moonshot API key. Optional; used for translation in PDF-to-PPT workflow.',
      ANTHROPIC_API_KEY: 'Anthropic API key. Optional; used by the AI parser when available.',
      OPENAI_API_KEY: 'OpenAI API key. Optional fallback for the AI parser.'
    }
  }
};

function parseEnv(content) {
  const values = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) {
      continue;
    }
    const idx = line.indexOf('=');
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, '');
    values[key] = value;
  }
  return values;
}

function serializeEnv(skillName, spec, values) {
  const lines = [
    '# Aut_Sci_Write per-skill environment file.',
    '# This file may contain API keys. Do not commit, publish, or redistribute it.',
    `# Skill: ${skillName}`,
    `# Purpose: ${spec.description}`,
    ''
  ];

  for (const [key, help] of Object.entries(spec.vars)) {
    lines.push(`# ${help}`);
    lines.push(`${key}=${values[key] || ''}`);
    lines.push('');
  }

  return lines.join('\n');
}

function ensureIgnoreEntry(filePath, entry) {
  let content = '';
  if (fs.existsSync(filePath)) {
    content = fs.readFileSync(filePath, 'utf8');
  }

  const entries = new Set(
    content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
  );

  if (entries.has(entry)) {
    return false;
  }

  const prefix = content && !content.endsWith('\n') ? '\n' : '';
  fs.appendFileSync(filePath, `${prefix}${entry}\n`, 'utf8');
  return true;
}

function readInstalledEnvValues(installedSkillNames) {
  const envBySkill = {};
  const valuesByKey = {};
  const conflicts = [];

  for (const skillName of installedSkillNames) {
    const envPath = path.join(SKILLS_DIR, skillName, '.env');
    const values = fs.existsSync(envPath)
      ? parseEnv(fs.readFileSync(envPath, 'utf8'))
      : {};
    envBySkill[skillName] = values;

    for (const [key, value] of Object.entries(values)) {
      if (!value) {
        continue;
      }
      if (valuesByKey[key] === undefined) {
        valuesByKey[key] = { value, source: `${skillName}/.env` };
      } else if (valuesByKey[key].value !== value) {
        // Same key set to different non-empty values in multiple skills.
        // The first-seen value wins; warn so the user knows which is used.
        conflicts.push(
          `${key}: keeping ${valuesByKey[key].source}, ignoring different value in ${skillName}/.env`
        );
      }
    }
  }

  return { envBySkill, valuesByKey, conflicts };
}

export function initializeSkillEnvs() {
  if (!fs.existsSync(SKILLS_DIR)) {
    return {
      created: [],
      updated: [],
      synced: [],
      conflicts: [],
      skipped: true,
      message: '[Aut_Sci_Write] No skills directory found; skipped .env initialization.'
    };
  }

  const installedSkillNames = Object.keys(SKILL_ENV_SPEC)
    .filter((skillName) => fs.existsSync(path.join(SKILLS_DIR, skillName)));

  if (installedSkillNames.length === 0) {
    return {
      created: [],
      updated: [],
      synced: [],
      conflicts: [],
      skipped: true,
      message: '[Aut_Sci_Write] No configurable skills found; skipped .env initialization.'
    };
  }

  const { envBySkill, valuesByKey, conflicts } = readInstalledEnvValues(installedSkillNames);
  const created = [];
  const updated = [];
  const synced = [];

  ensureIgnoreEntry(path.join(ROOT_DIR, '.gitignore'), '.env');

  for (const skillName of installedSkillNames) {
    const skillDir = path.join(SKILLS_DIR, skillName);
    const envPath = path.join(skillDir, '.env');
    const gitignorePath = path.join(skillDir, '.gitignore');
    const spec = SKILL_ENV_SPEC[skillName];
    const values = { ...envBySkill[skillName] };
    const existed = fs.existsSync(envPath);

    ensureIgnoreEntry(gitignorePath, '.env');

    for (const key of Object.keys(spec.vars)) {
      if (!values[key] && valuesByKey[key]?.value) {
        values[key] = valuesByKey[key].value;
        synced.push(`${key}: ${valuesByKey[key].source} -> ${skillName}/.env`);
      }
    }

    const next = serializeEnv(skillName, spec, values);
    const previous = existed ? fs.readFileSync(envPath, 'utf8') : '';
    if (!existed || previous !== next) {
      fs.writeFileSync(envPath, next, 'utf8');
      (existed ? updated : created).push(path.relative(ROOT_DIR, envPath));
    }
  }

  let message = '[Aut_Sci_Write] Per-skill .env files are already initialized.';
  if (created.length || updated.length || synced.length) {
    message = '[Aut_Sci_Write] Per-skill .env initialization complete.';
  }

  return {
    created,
    updated,
    synced,
    conflicts,
    skipped: false,
    message
  };
}

function printResult(result) {
  console.log(result.message);
  if (result.created.length) {
    console.log(`  Created: ${result.created.join(', ')}`);
  }
  if (result.updated.length) {
    console.log(`  Updated: ${result.updated.join(', ')}`);
  }
  if (result.synced.length) {
    console.log(`  Reused duplicate config: ${result.synced.join('; ')}`);
  }
  if (result.conflicts?.length) {
    console.log(`  Warning: conflicting values for shared keys: ${result.conflicts.join('; ')}`);
  }
  console.log('  Notice: .env files may contain API keys. Do not commit, publish, or redistribute them.');
}

if (path.resolve(process.argv[1] || '') === __filename) {
  printResult(initializeSkillEnvs());
}
