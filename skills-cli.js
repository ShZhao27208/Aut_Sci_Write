#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import os from 'os';

const SKILLS_DIR = path.join(
  process.env.HOME || process.env.USERPROFILE || os.homedir(),
  '.claude',
  'skills',
  'omc-learned'
);

function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) {
    return null;
  }

  const metadata = {};
  let currentListKey = null;

  for (const rawLine of match[1].split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      continue;
    }

    const listMatch = line.match(/^\s*-\s*(.+)$/);
    if (listMatch && currentListKey) {
      metadata[currentListKey].push(listMatch[1].trim().replace(/^['"]|['"]$/g, ''));
      continue;
    }

    const fieldMatch = line.match(/^([^:]+):\s*(.*)$/);
    if (!fieldMatch) {
      continue;
    }

    const key = fieldMatch[1].trim();
    const value = fieldMatch[2].trim();
    if (value === '') {
      metadata[key] = [];
      currentListKey = key;
      continue;
    }

    metadata[key] = value.replace(/^['"]|['"]$/g, '');
    currentListKey = null;
  }

  return metadata;
}

function readSkillMetadata(skillPath) {
  const skillFile = path.join(skillPath, 'SKILL.md');
  if (!fs.existsSync(skillFile)) {
    return null;
  }

  const content = fs.readFileSync(skillFile, 'utf8');
  const metadata = parseFrontmatter(content);
  if (!metadata) {
    return null;
  }

  return metadata;
}

function collectSkills() {
  if (!fs.existsSync(SKILLS_DIR)) {
    return { error: `Skills directory not found: ${SKILLS_DIR}`, skills: [] };
  }

  const skills = fs.readdirSync(SKILLS_DIR)
    .filter((entry) => fs.statSync(path.join(SKILLS_DIR, entry)).isDirectory())
    .map((name) => {
      const metadata = readSkillMetadata(path.join(SKILLS_DIR, name)) || {};
      return { name, ...metadata };
    });

  return { skills };
}

function printSkill(skill, index = null) {
  const prefix = index === null ? '- ' : `${index}. `;
  console.log(`${prefix}${skill.name}`);
  if (skill.description) {
    console.log(`  Description: ${skill.description}`);
  }
  if (Array.isArray(skill.triggers) && skill.triggers.length > 0) {
    console.log(`  Triggers: ${skill.triggers.join(', ')}`);
  }
}

function listSkills() {
  const { error, skills } = collectSkills();
  if (error) {
    console.error(error);
    process.exitCode = 1;
    return;
  }

  if (skills.length === 0) {
    console.log('No skills found.');
    return;
  }

  console.log('Academic Skills Installed');
  console.log('');
  skills.forEach((skill, idx) => {
    printSkill(skill, idx + 1);
    console.log('');
  });
  console.log(`Total: ${skills.length}`);
}

function searchSkills(query) {
  const { error, skills } = collectSkills();
  if (error) {
    console.error(error);
    process.exitCode = 1;
    return;
  }

  const normalized = query.toLowerCase();
  const results = skills.filter((skill) => {
    const haystack = [
      skill.name,
      skill.description || '',
      ...(Array.isArray(skill.triggers) ? skill.triggers : []),
    ].join(' ').toLowerCase();
    return haystack.includes(normalized);
  });

  if (results.length === 0) {
    console.log(`No skills found matching "${query}".`);
    return;
  }

  console.log(`Found ${results.length} skill(s) matching "${query}":`);
  console.log('');
  results.forEach((skill) => {
    printSkill(skill);
    console.log('');
  });
}

function showHelp() {
  console.log(`Claude Academic Skills - Local Discovery Tool

Usage:
  skills-cli list
  skills-cli search <query>
  skills-cli help
`);
}

const command = process.argv[2];
const arg = process.argv[3];

switch (command) {
  case 'list':
    listSkills();
    break;
  case 'search':
    if (!arg) {
      console.error('Please provide a search query.');
      showHelp();
      process.exitCode = 1;
    } else {
      searchSkills(arg);
    }
    break;
  case 'help':
  case '--help':
  case '-h':
    showHelp();
    break;
  default:
    listSkills();
    break;
}
