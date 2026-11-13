// @namja_sokmaeum 자동 업로드 스크립트
// posts.json에서 아직 안 올린 게시물 1개를 골라 인스타그램에 캐러셀로 올린다.
//
// 필요한 환경변수
//   IG_TOKEN        Meta 개발자 화면에서 받은 액세스 토큰
//   IG_USER_ID      (선택) 인스타 계정 ID. 비우면 토큰으로 자동 확인
//   IMAGE_BASE_URL  out/ 폴더 이미지가 공개된 주소 (끝에 / 없이)
//   MODE            check   = 토큰·계정 연결 확인만
//                   dry_run = 올릴 게시물만 확인
//                   publish = 실제 업로드 (기본값)
//
// 실행: node publish.mjs

import { readFile, writeFile } from "node:fs/promises";

const HOSTS = ["https://graph.instagram.com/v26.0", "https://graph.facebook.com/v26.0"];
const { IG_TOKEN, IMAGE_BASE_URL } = process.env;
const MODE = process.env.MODE || "publish";
let API = HOSTS[0];
let IG_USER_ID = process.env.IG_USER_ID;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, path, params = {}) {
  const body = new URLSearchParams({ ...params, access_token: IG_TOKEN });
  const url = method === "GET" ? `${API}${path}?${body}` : `${API}${path}`;
  const res = await fetch(url, method === "GET" ? {} : { method, body });
  const json = await res.json();
  if (!res.ok || json.error) {
    throw new Error(`${method} ${path} 실패: ${JSON.stringify(json.error ?? json)}`);
  }
  return json;
}

// 컨테이너가 FINISHED가 될 때까지 대기 (최대 5분)
async function waitReady(containerId) {
  for (let i = 0; i < 20; i++) {
    const { status_code } = await api("GET", `/${containerId}`, { fields: "status_code" });
    if (status_code === "FINISHED") return;
    if (status_code === "ERROR" || status_code === "EXPIRED") {
      throw new Error(`컨테이너 ${containerId} 상태: ${status_code}`);
    }
    await sleep(15_000);
  }
  throw new Error(`컨테이너 ${containerId} 준비 시간 초과`);
}

// 토큰이 어느 API 주소에서 동작하는지, 어떤 계정인지 자동으로 확인
async function detect() {
  if (!IG_TOKEN) throw new Error("IG_TOKEN 환경변수가 필요해요.");
  const tryGet = async (host, path, fields) => {
    const r = await fetch(`${host}${path}?fields=${fields}&access_token=${IG_TOKEN}`);
    const j = await r.json();
    return r.ok && !j.error ? j : null;
  };
  // 1) 인스타그램 로그인 방식 (graph.instagram.com)
  const ig = await tryGet(HOSTS[0], "/me", "user_id,username,account_type");
  if (ig) {
    API = HOSTS[0];
    IG_USER_ID ||= ig.user_id;
    return `graph.instagram.com / @${ig.username} (${ig.account_type}) / ID ${IG_USER_ID}`;
  }
  // 2) 페이스북 로그인·시스템 사용자 방식 (graph.facebook.com)
  if (IG_USER_ID) {
    const fb = await tryGet(HOSTS[1], `/${IG_USER_ID}`, "username");
    if (fb) {
      API = HOSTS[1];
      return `graph.facebook.com / @${fb.username} / ID ${IG_USER_ID}`;
    }
  }
  const me = await tryGet(HOSTS[1], "/me", "id,name");
  throw new Error(
    me
      ? `토큰은 유효하지만 인스타 계정을 못 찾았어요. IG_USER_ID 시크릿에 개발자 화면의 Instagram 계정 ID를 넣어주세요. (토큰 주인: ${me.name})`
      : "토큰이 유효하지 않아요. 복사가 잘렸는지 확인하세요."
  );
}

async function main() {
  console.log("연결 확인:", await detect());
  if (MODE === "check") {
    const limit = await api("GET", `/${IG_USER_ID}/content_publishing_limit`, { fields: "quota_usage" });
    console.log("게시 권한 OK, 오늘 사용량:", JSON.stringify(limit.data?.[0] ?? limit));
    return;
  }
  const posts = JSON.parse(await readFile("posts.json", "utf8"));
  const published = JSON.parse(await readFile("published.json", "utf8"));
  const done = new Set(published.map((p) => p.id));

  const post = posts.find((p) => !done.has(p.id));
  if (!post) {
    console.log("올릴 게시물이 없어요. posts.json에 새 게시물을 추가하세요.");
    return;
  }

  const urls = post.slides.map(
    (_, i) => `${IMAGE_BASE_URL}/${post.id}_${String(i + 1).padStart(2, "0")}.jpg`
  );
  console.log(`게시물 ${post.id} (${urls.length}장)`);

  // 이미지가 실제로 공개돼 있는지 먼저 확인
  for (const u of urls) {
    const r = await fetch(u, { method: "HEAD" });
    if (!r.ok) throw new Error(`이미지에 접근할 수 없어요 (${r.status}): ${u}`);
  }

  if (MODE === "dry_run") {
    console.log("[DRY_RUN] 올릴 이미지:\n" + urls.join("\n"));
    console.log("[DRY_RUN] 캡션:\n" + post.caption);
    return;
  }
  // 사용량 확인
  const limit = await api("GET", `/${IG_USER_ID}/content_publishing_limit`, {
    fields: "quota_usage,config",
  });
  console.log("오늘 사용량:", JSON.stringify(limit.data?.[0] ?? limit));

  let creationId;
  if (urls.length === 1) {
    const c = await api("POST", `/${IG_USER_ID}/media`, { image_url: urls[0], caption: post.caption });
    creationId = c.id;
  } else {
    const children = [];
    for (const u of urls) {
      const c = await api("POST", `/${IG_USER_ID}/media`, { image_url: u, is_carousel_item: "true" });
      children.push(c.id);
    }
    for (const id of children) await waitReady(id);
    const carousel = await api("POST", `/${IG_USER_ID}/media`, {
      media_type: "CAROUSEL",
      children: children.join(","),
      caption: post.caption,
    });
    creationId = carousel.id;
  }

  await waitReady(creationId);
  const { id: mediaId } = await api("POST", `/${IG_USER_ID}/media_publish`, { creation_id: creationId });
  console.log(`업로드 완료! media id: ${mediaId}`);

  published.push({ id: post.id, mediaId, at: new Date().toISOString() });
  await writeFile("published.json", JSON.stringify(published, null, 2) + "\n");
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
