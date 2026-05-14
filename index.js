import { initializeSkillEnvs, SKILL_ENV_SPEC } from './init-env.js';

export const packageName = 'shuozhao-academic-skills';
export const configurableSkills = Object.freeze(Object.keys(SKILL_ENV_SPEC));
export { initializeSkillEnvs, SKILL_ENV_SPEC };

export default {
  packageName,
  configurableSkills,
  initializeSkillEnvs,
};
