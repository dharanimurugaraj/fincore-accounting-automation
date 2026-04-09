import { PrismaClient } from "@prisma/client";
import "dotenv/config";

const prisma = new PrismaClient({
  datasourceUrl: process.env.DATABASE_URL,
});

async function main() {
  console.log('🌱 Seeding database...');

  // 1. Roles
  const roles = [
    { id: 0, name: 'SUPER_ADMIN', description: 'Platform-wide total access', allowedPages: ['*'] },
    { id: 1, name: 'ADMIN', description: 'Organization-level administration', allowedPages: ['*'] },
    { id: 2, name: 'ANALYST', description: 'Standard organization user', allowedPages: ['Dashboard', 'Upload', 'Documents', 'Reports', 'WCDL Tracker', 'Forex Register', 'Activity'] },
    { id: 3, name: 'VIEWER', description: 'Read-only organization access', allowedPages: ['Dashboard', 'Reports'] },
    { id: 4, name: 'PENDING_APPROVAL', description: 'User awaiting administrator confirmation', allowedPages: [] },
  ];

  for (const role of roles) {
    await prisma.role.upsert({
      where: { id: role.id },
      update: {
          name: role.name,
          description: role.description,
          allowedPages: role.allowedPages
      },
      create: role,
    });
  }
  console.log('✅ Roles seeded.');

  // 2. Default Organisation
  await prisma.organisation.upsert({
    where: { id: 'default-org' },
    update: {},
    create: {
      id: 'default-org',
      name: 'Vyrenzo Bank Demo',
      legalName: 'Vyrenzo Financial Services Ltd.',
      departments: ['Investment Banking', 'Asset Management', 'Operations'],
    },
  });
  console.log('✅ Default organisation seeded.');

  console.log('🚀 Seeding complete.');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
