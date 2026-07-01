<template>
  <footer class="footer">
    <div class="wrap footer-body">
      <div class="footer-brand">
        <img src="../assets/logo.png" alt="StratMaster CS2" class="footer-logo" />
        <p>Premium CS2 strategies and tactics<br>from esports professionals.</p>
      </div>

      <div class="footer-col">
        <h4>Navigate</h4>
        <ul>
          <li><a href="#strategies">Strategies</a></li>
          <li><a href="#strategies">Maps</a></li>
          <li><a href="#pricing">Pricing</a></li>
        </ul>
      </div>

      <div class="footer-col">
        <h4>Support</h4>
        <ul>
          <li><a href="https://t.me/+xyLN_GYPgvI5YWUy">Contact</a></li>
        </ul>
      </div>

      <div class="footer-col">
        <h4>Community</h4>
        <div class="socials">
          <a href="https://t.me/stratMasterCS2" class="social">Telegram</a>
        </div>
      </div>
    </div>

    <div class="footer-bottom">
      <div class="wrap">
        <span>© 2025 StratMaster CS2. All rights reserved.</span>
        <span class="footer-tag">Built for winners.</span>
      </div>
    </div>
  </footer>
</template>

<script setup></script>

<style scoped>
.footer {
  margin-top: 100px;
  border-top: 1px solid var(--line);
}
.footer-body {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 48px;
  padding: 64px 20px 48px;
}
.footer-logo {
  height: 32px;
  width: auto;
  object-fit: contain;
  margin-bottom: 16px;
  display: block;
}
.footer-brand p {
  color: var(--text-dim);
  font-size: 14px;
  line-height: 1.7;
}
.footer-col h4 {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text);
  margin-bottom: 16px;
}
.footer-col ul { list-style: none; display: flex; flex-direction: column; gap: 10px; }
.footer-col ul li a,
.social {
  color: var(--text-dim);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.footer-col ul li a:hover,
.social:hover { color: var(--accent); }
.socials { display: flex; flex-direction: column; gap: 10px; }

.footer-bottom {
  border-top: 1px solid var(--line);
  padding: 18px 20px;
}
.footer-bottom .wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.footer-bottom span {
  color: var(--text-dim);
  font-size: 13px;
}
.footer-tag {
  color: var(--accent) !important;
  font-weight: 700;
  letter-spacing: 0.04em;
}

@media (max-width: 700px) {
  .footer-body { grid-template-columns: 1fr 1fr; gap: 32px; }
  .footer-brand { grid-column: 1 / -1; }
}
@media (max-width: 420px) {
  .footer-body { grid-template-columns: 1fr; }
}
</style>