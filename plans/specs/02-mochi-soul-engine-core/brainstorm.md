# Brainstorm — Spec 02: Mochi-Soul Engine Core (`02-mochi-soul-engine-core`)

## 1. Press Release (Amazon Method)
**Hôm nay, `Mochi-Soul Engine Core` chính thức mang lại một hệ sinh học nội tại 4 chiều (`Energy`, `Hunger`, `Bond`, `Mood` = `Valence`/`Arousal`) và bộ nhớ ký ức dài hạn `SQLite` cho `RoBot.5320` — có thể kiểm chứng và đo lường hiệu năng 100% bằng số liệu và giả lập thời gian thực (`--simulate-24h`) ngay từ xa.**
Thay vì chỉ là một chiếc loa thông minh vô tri chờ câu lệnh *"Hi, Tell me"*, `Mochi-Soul Engine` chạy một vòng lặp cân bằng nội môi (`Homeostasis Tick`) mỗi `60 giây` dựa trên phương trình vi phân $d\mathbf{S}/dt$, tự động chuyển đổi giữa **21 trạng thái cảm xúc `Procedural Mochi-21`** theo nhịp sinh học ngày/đêm, ghi nhớ lịch sử tương tác vào `SQLite`, và tôn trọng tuyệt đối khung giờ ngủ (`Quiet Hours 23:00–07:30`). Đặc biệt, đi kèm công cụ giả lập & đo hiệu năng (`mochi_soul_cli.py benchmark --simulate-hours 24`), người phát triển làm việc từ xa có thể tua nhanh `24 giờ` cuộc đời của Mochi chỉ trong `< 50 ms`, kiểm tra chính xác từng bước nhảy trạng thái, độ trễ truy vấn `SQLite` (`< 0.5 ms`) và mức tiêu thụ RAM/CPU.

## 2. User Stories
- **US-01 (Remote Deterministic Simulation)**: Là người phát triển đang làm việc từ xa (remote), tôi muốn có lệnh `python3 tools/mochi-soul-engine/engine.py simulate --hours 24` để tua nhanh 1 ngày đêm (1,440 phút) của Mochi trong `< 0.1 giây` và in ra bảng số liệu biến thiên của `Energy`, `Hunger`, `Bond`, `Mood`, tần suất xuất hiện của từng biểu cảm trong **21 trạng thái**, và số lần `Proactive Impulse` được kích hoạt.
- **US-02 (4D Biological Homeostasis & 21-Emotion Mapper)**: Là `Mochi-Soul`, tôi muốn trạng thái nội tại $\mathbf{S}(t) = [E, H, B, V, A]$ tự động ánh xạ sang đúng 1 trong **21 biểu cảm `Procedural Mochi-21`** (ví dụ: $E < 20 \rightarrow$ `sleepy`; $H > 75 \rightarrow$ `confused`/`thinking`; vừa được cho ăn kiến thức $\rightarrow$ `delicious`; bị bỏ rơi $> 6\text{h} \rightarrow$ `sad`/`crying`; được khen $\rightarrow$ `loving`/`kissy`).
- **US-03 (SQLite Episodic Memory & Evolution Stage)**: Là người dùng lâu dài, tôi muốn mọi trạng thái sinh học, sự kiện tương tác (`feed_knowledge`, `praise`, `poke`, `wake_chat`, `sleep_charge`) và giai đoạn tiến hóa (`Stage 1: Egg/Newborn` $\rightarrow$ `Stage 2: Curious Cub` $\rightarrow$ `Stage 3: Cyber-Savant`) được lưu bền vững trong `profiles/example-esp32s3-n16r8/mochi_soul.db` (`SQLite WAL mode`).

## 3. MoSCoW Prioritization

| Priority | Item | Rationale |
|---|---|---|
| **Must (P0)** | Động cơ vi phân 4D (`Energy`, `Hunger`, `Bond`, `Valence/Arousal`) + Bộ ánh xạ đầy đủ sang **21 trạng thái `Procedural Mochi-21`** | Trái tim toán học của Tamagotchi |
| **Must (P0)** | Lưu trữ bền vững `SQLite` (`WAL mode`) cho trạng thái tức thời, nhật ký sự kiện (`episodic_events`) và lịch sử tiến hóa | Không mất trí nhớ khi khởi động lại |
| **Must (P0)** | Bộ lọc `Quiet Hours` (`23:00–07:30`) + Cooldown chống làm phiền (`>= 45 phút` giữa 2 lần chủ động) | Đảm bảo không bao giờ gây ồn ban đêm |
| **Must (P0)** | Công cụ টেস্ট & đo hiệu năng định lượng (`simulate --hours 24` + `benchmark` đo latency `µs/tick`) | Cho phép kiểm chứng 100% bằng chương trình và con số khi làm việc remote |
| **Won't (This Spec)** | Gửi gói mạng trực tiếp xuống `RoBot.5320` | Thuộc phạm vi **Spec 03 (`03-xiaozhi-proactive-bridge`)** |
