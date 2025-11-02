#!/usr/bin/env node
const BASE_URL = process.env.VBUDGET_BASE_URL ?? 'http://localhost:8000';

const ADMIN_EMAIL = process.env.VBUDGET_ADMIN_EMAIL ?? 'rehan@voiceworx.in';
const ADMIN_PASSWORD = process.env.VBUDGET_ADMIN_PASSWORD ?? 'Admin@123';

async function postJson(path, body, token) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`POST ${path} failed (${response.status}): ${text}`);
  }
  return response.json();
}

async function postForm(path, form) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams(form),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`POST ${path} failed (${response.status}): ${text}`);
  }
  return response.json();
}

async function getDebugOtp(email, purpose) {
  const url = new URL(`${BASE_URL}/debug/otps`);
  if (email) url.searchParams.set('email', email);
  if (purpose) url.searchParams.set('purpose', purpose);
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`GET /debug/otps failed (${response.status}): ${text}`);
  }
  const data = await response.json();
  if (!Array.isArray(data) || data.length === 0) {
    throw new Error(`No OTPs available yet for ${email ?? 'any user'} (${purpose ?? 'any purpose'})`);
  }
  return data[0].code;
}

async function login(email, password) {
  const tokenResponse = await postForm('/auth/login', { username: email, password });
  return tokenResponse.access_token;
}

async function main() {
  console.log('🚀 Running V-Budget guided workflow');
  console.log(`➡️  Target API: ${BASE_URL}`);

  const unique = Math.floor(Math.random() * 1_000_000);
  const employeeEmail = `demo${unique}@vb.test`;

  console.log('\n1️⃣  Registering a new employee');
  const registerResponse = await postJson('/auth/register', {
    name: 'Demo User',
    email: employeeEmail,
    phone: '9999999999',
    designation: 'Executive',
    team: 'Events',
    supervisor: 'Rehan',
    password: 'Welcome@123',
  });
  console.log(`   ✅ Registered user id ${registerResponse.id} (${employeeEmail})`);

  console.log('\n2️⃣  Completing self-OTP verification');
  const selfOtp = await getDebugOtp(employeeEmail, 'self_registration');
  await postJson('/auth/verify-self', { email: employeeEmail, otp: selfOtp });
  console.log(`   🔐 Self OTP ${selfOtp} consumed`);

  console.log('\n3️⃣  Approving the employee as admin');
  const adminToken = await login(ADMIN_EMAIL, ADMIN_PASSWORD);
  const adminOtp = await getDebugOtp(employeeEmail, 'admin_approval');
  await postJson(
    '/auth/admin-approve',
    { user_id: registerResponse.id, otp: adminOtp },
    adminToken,
  );
  console.log(`   🧾 Admin approval OTP ${adminOtp} applied`);

  console.log('\n4️⃣  Logging in as the new employee');
  const employeeToken = await login(employeeEmail, 'Welcome@123');
  console.log('   ✅ Employee JWT obtained');

  console.log('\n5️⃣  Requesting vendor drawer OTP');
  await postJson('/vendors/request-otp', {}, employeeToken);
  const vendorOtp = await getDebugOtp(employeeEmail, 'vendor_unlock');
  console.log(`   🔑 Vendor OTP ${vendorOtp} ready`);

  console.log('\n6️⃣  Creating a sample vendor');
  const vendorResponse = await postJson(
    '/vendors',
    {
      otp: vendorOtp,
      vendor: {
        name: 'Aurora Sound & Light',
        category: 'Sound',
        contact_person: 'Rahul',
        phone: '9876543210',
        email: 'aurora@example.com',
        gst_number: '27ABCDE1234F1Z5',
        region: 'Mumbai',
        rate_cards: [
          {
            item_name: 'Line Array',
            description: '12 box line array with rigging',
            unit: 'per event',
            rate: 95000,
            min_quantity: 1,
            setup_charges: 5000,
            notes: 'Includes transportation within Mumbai',
            category_tag: 'Sound',
          },
        ],
      },
    },
    employeeToken,
  );
  console.log(`   📦 Vendor ${vendorResponse.name} created with status ${vendorResponse.status}`);

  console.log('\n✅ Workflow complete. Continue in Swagger UI to build budgets and approvals.');
}

main().catch((error) => {
  console.error('\n❌ Demo failed:', error.message);
  process.exit(1);
});
