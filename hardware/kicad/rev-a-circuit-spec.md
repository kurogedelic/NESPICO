# NESPICO Rev.A 回路仕様案

**状態:** 論理回路候補 v0.3。機能回路図・論理検査・一般的な14-pin 74-seriesゲートの候補ピン割当はあるが、KiCad上の実ゲート実装、実発注パッケージ、電源・保護・音声回路、PIO波形/CPU・PPU同時動作は未検証。基板設計・製造用ではない。

## 1. 設計方針

初号からFamicom 60ピンのフルライブ接続を目標とする。CPUとPPUは独立した8-bitレーンを維持する。GP26–GP28はADC0–ADC2としてアナログ専用にし、GP29/ADC3はPico 2のVSYS測定用として外部接続しない。

現時点ではCPLDを必須部品にしない。各レーンのアドレスを74AHCT573で保持し、74AHCT74/74AHCT00/04/08で2バイト順序と制御を行う候補とする。これは以前の「CPLDを使うかもしれない」という案からの簡素化で、CPLD等の追加ロジックを許容するという希望には合致するが、CPLDは選ばない判断である。ピン数が収まる見通しは立ったものの、PIOの実時間・競合テストに失敗したらCPLD案へ戻す。

## 2. Pico 2論理信号割当

下表は論理GPIO名の割当であり、物理ピン番号・モジュールのヘッダ・フットプリントはまだ決めない。

| RP2350信号 | 役割 | 方向 | 回路上の扱い |
| --- | --- | --- | --- |
| GP0–GP7 | CPU D0–D7 | 双方向 | Pico→バスAHCT244とバス→Pico LVC244Aを分離 |
| GP8–GP15 | PPU D0–D7／待機時ステータス | 双方向I/O | PPU read:入力、write:出力、idle:status入力。送受信AHCT244/LVC244AとLVC257Aで分離 |
| GP16 | CPU M2 | 出力 | 5V AHCT制御バッファを介してカートへ |
| GP17 | CPU R/W | 出力 | 同上。H=read、L=write |
| GP18 | PPU /RD | 出力 | 同上。active-low |
| GP19 | PPU /WR | 出力 | 同上。active-low |
| GP20 | CPU_ADDR_STB | 出力 | CPUアドレス下位・上位ラッチを交互選択 |
| GP21 | PPU_ADDR_STB | 出力 | PPUアドレス下位・上位ラッチを交互選択 |
| GP22 | APU_AUDIO_PWM | 出力 | フィルタ／減衰段を介してピン45へ。値は音声実測後に決める |
| GP26 / ADC0 | CART_AUDIO_RET | 入力 | ピン46からの音声フロントエンド。3.3V範囲とバイアスを要実測確認 |
| GP27 / ADC1 | CART_5V_SENSE | 入力 | +5V_CARTを分圧・RCフィルタして監視 |
| GP28 / ADC2 | ADC2_AUX | 入力 | アナログ予備入力／テストパッド。デジタル転用しない |
| GP29 / ADC3 | VSYS_MONITOR | 内部 | 基板外へ接続しない |

これでGP0–GP22を使い切る。GP26–GP28はアナログのみ、GP29は未配線とする。

## 3. アドレス保持と2バイト位相

CPUとPPUの各8-bitデータレーンを、アドレス更新時に一時的にアドレス値の運搬にも使う。各レーンに下位・上位のSN74AHCT573を1個ずつ置く。573のLEはHで透明、Lで保持する。各バスにSN74AHCT74の位相FFを1個割り当て、初期位相を下位バイト（Q=0）とする。

```text
PHASE_CLK = NOT(ADDR_STB)        # AHCT74の正エッジはADDR_STBの立下り
BUS_RUN   = RUN_N AND PWR_GOOD  # RUN_N=Hかつ5V監視正常のときだけ動作
BUS_OE_N  = NOT(BUS_RUN)        # リセット／電源異常時に外部出力をHi-Z
PHASE_CLR_N = BUS_RUN           # AHCT74の/CLRも同じ安全条件で保持
LE_LOW    = BUS_RUN AND ADDR_STB AND NOT(Q)
LE_HIGH   = BUS_RUN AND ADDR_STB AND Q
D         = NOT(Q)               # 各ADDR_STBの立下りごとに位相反転
```

ADDR_STBがHの間だけ選択中の573が透明になり、立下りで閉じる。その立下りでFFのQを切り替えるが、ADDR_STBは既にLなのでLE_LOW/LE_HIGHに追加パルスは発生しない。`RUN_N=L`または`PWR_GOOD=L`ならBUS_RUN=Lとなり、AHCT74のactive-low `/CLR`をアサートしてQ=0、全ラッチLE=L、バッファOE_N=Hとする。CPU/PPUの各更新は**下位バイト、上位バイトの順に2ストローブを必ず一組で発行**する。片方だけ更新する場合も両方を再発行し、位相をずらさない。PIOでデータsetup/hold、strobe幅、CPU/PPU独立動作を実測すること。

| 候補部品 | 個数 | 役割 |
| --- | ---: | --- |
| SN74AHCT573 | 4 | CPU下位/上位、PPU下位/上位の各8-bitアドレス保持 |
| SN74AHCT74 | 1 | CPU/PPUの独立した位相FF（2チャネル） |
| SN74AHCT04 | 2 | `/ADDR_STB`、`/PPU_A13`、`/CPU_RW`、PPU制御、BUS_OE_N、`/ROMSEL`等の反転（9/12 gates used） |
| SN74AHCT08 | 4 | BUS_RUN、CPU/PPUバス選択、方向判定、status select、アドレスLE生成（14/16 gates used） |
| SN74AHCT00 | 2 | CPU/PPU transceiver OEとアドレス転送中に不活性化するカート制御（7/8 gates used） |

この論理IC数と個別gate/pin割当は候補であり、次節に記す。実発注packageとの一致、KiCad実ゲート配置、未使用入力の固定、footprint、デカップリングは未検証。573のOE_NはBUS_OE_Nで制御し、リセット時にHとなる。AHCTのデータシート推奨どおり安全なプルアップを含める。3.3V GPIOはAHCT入力のTTLしきい値で扱う。

### 3.1 制御ゲートの候補ピン割当

下表はSN74AHCT08/00/04の標準14-pin論理配置に対する候補割当で、KiCad上の実ゲート配置・製品パッケージの承認ではない。1ゲートのpin順はAHCT08/00で `A,B→Y`、AHCT04で `A→Y`。VCC=pin14、GND=pin7。製造元ピン図は[TI SN74AHCT08](https://www.ti.com/lit/ds/symlink/sn74ahct08.pdf)、[SN74AHCT00](https://www.ti.com/lit/ds/symlink/sn74ahct00.pdf)、[SN74AHCT04](https://www.ti.com/lit/ds/symlink/sn74ahct04.pdf)を参照。

| IC / gate | 入力ピン → 出力ピン | 信号式 |
| --- | --- | --- |
| U18A | 1,2 → 3 | `RUN_N AND PWR_GOOD → BUS_RUN` |
| U18B | 4,5 → 6 | `BUS_RUN AND CPU_STB_N → CPU_STB_RUN` |
| U18C | 9,10 → 8 | `CPU_STB_RUN AND GP16_M2 → M2_CTRL` |
| U18D | 12,13 → 11 | `M2_CTRL AND CPU_A15 → CPU_CART_ACTIVE` |
| U19A | 1,2 → 3 | `BUS_RUN AND PPU_STB_N → PPU_STB_RUN` |
| U19B | 4,5 → 6 | `PPU_STB_RUN AND PPU_RD → PPU_READ_BASE` |
| U19C | 9,10 → 8 | `PPU_STB_RUN AND PPU_RD_N → PPU_WRITE_BASE` |
| U19D | 12,13 → 11 | `PPU_WRITE_BASE AND PPU_WR_N → PPU_STATUS_EN` |
| U20A | 1,2 → 3 | `BUS_RUN AND GP20_CPU_ADDR_STB → CPU_ADDR_BASE` |
| U20B | 4,5 → 6 | `CPU_ADDR_BASE AND CPU_PHASE_N → CPU_LE_LOW` |
| U20C | 9,10 → 8 | `CPU_ADDR_BASE AND CPU_PHASE → CPU_LE_HIGH` |
| U20D | 12,13 → 11 | `BUS_RUN AND GP21_PPU_ADDR_STB → PPU_ADDR_BASE` |
| U21A | 1,2 → 3 | `PPU_ADDR_BASE AND PPU_PHASE_N → PPU_LE_LOW` |
| U21B | 4,5 → 6 | `PPU_ADDR_BASE AND PPU_PHASE → PPU_LE_HIGH` |
| U21C/U21D | unused | inputs tied to GND; outputs NC |

| IC / gate | 入力ピン → 出力ピン | 信号式 |
| --- | --- | --- |
| U22A | 1,2 → 3 | `NAND(CPU_RW_N, CPU_STB_N) → CPU_RW_CTRL` |
| U22B | 4,5 → 6 | `NAND(PPU_RD, PPU_STB_N) → PPU_RD_N_CTRL` |
| U22C | 9,10 → 8 | `NAND(PPU_WR, PPU_STB_N) → PPU_WR_N_CTRL` |
| U22D | 12,13 → 11 | `NAND(CPU_CART_ACTIVE, CPU_RW_N) → CPU_TX_OE_N` |
| U23A | 1,2 → 3 | `NAND(CPU_CART_ACTIVE, CPU_RW) → CPU_RX_OE_N` |
| U23B | 4,5 → 6 | `NAND(PPU_READ_BASE, PPU_WR_N) → PPU_RX_OE_N` |
| U23C | 9,10 → 8 | `NAND(PPU_WRITE_BASE, PPU_WR) → PPU_TX_OE_N` |
| U23D | unused | inputs tied to GND; output NC |

| IC / gate | 入力ピン → 出力ピン | 信号式 |
| --- | --- | --- |
| U24A | 1 → 2 | `NOT(CPU_ADDR_STB) → CPU_STB_N` |
| U24B | 3 → 4 | `NOT(PPU_ADDR_STB) → PPU_STB_N` |
| U24C | 5 → 6 | `NOT(PPU_A13) → PPU_A13_N` |
| U24D | 9 → 8 | `NOT(CPU_RW) → CPU_RW_N` |
| U24E | 11 → 10 | `NOT(PPU_RD_N) → PPU_RD` |
| U24F | 13 → 12 | `NOT(PPU_WR_N) → PPU_WR` |
| U25A | 1 → 2 | `NOT(BUS_RUN) → BUS_OE_N` |
| U25B | 3 → 4 | `NOT(PPU_STATUS_EN) → PPU_STATUS_OE_N` |
| U25C | 5 → 6 | `NOT(CPU_CART_ACTIVE) → ROMSEL_N` |
| U25D–U25F | unused | inputs tied to GND; outputs NC |

U21C/DとU23Dは未使用。未使用AHCT04の入力もGNDへ固定して出力をNCとする。各ICのVCC–GND間に近接した100 nFデカップリングを置く候補とする。最終実装前に正確な注文型番のピン図、package選択、pull抵抗、ファンアウトと伝搬遅延を照合する。

## 4. データレーンと方向制御

各バスの送信・受信は別ICとし、同時駆動を論理的に禁止する。方向が固定の各8-bit経路にはSN74AHCT244（Pico→カート、5V）またはSN74LVC244A（カート→Pico、3.3V）を使う候補とする。どちらも出力はA→Yの一方向なので245のDIRは不要で、各ICのactive-low /OEを個別ゲートで制御する。SN74LVC244AはIoff/部分電源断対応で、3.3V電源断時の5V側からの逆流を抑える候補となる。

```text
CPU_STB_N = NOT(CPU_ADDR_STB)
CPU_STB_RUN = BUS_RUN AND CPU_STB_N
M2_CTRL = CPU_STB_RUN AND M2
CPU_CART_ACTIVE = M2_CTRL AND CPU_A15
ROMSEL_N = NOT(CPU_CART_ACTIVE)   # Famicom pin 44; inactive during address load/reset
CPU_RW_CTRL = CPU_RW OR CPU_ADDR_STB
CPU_TX   = CPU_CART_ACTIVE AND NOT(CPU_RW)
CPU_RX   = CPU_CART_ACTIVE AND CPU_RW
CPU_TX_OE_N = NOT(CPU_TX)
CPU_RX_OE_N = NOT(CPU_RX)

PPU_STB_N = NOT(PPU_ADDR_STB)
PPU_STB_RUN = BUS_RUN AND PPU_STB_N
PPU_READ_BASE = PPU_STB_RUN AND NOT(PPU_RD_N)
PPU_WRITE_BASE = PPU_STB_RUN AND PPU_RD_N
PPU_RD_N_CTRL = PPU_RD_N OR PPU_ADDR_STB
PPU_WR_N_CTRL = PPU_WR_N OR PPU_ADDR_STB
PPU_READ  = PPU_READ_BASE AND PPU_WR_N
PPU_WRITE = PPU_WRITE_BASE AND NOT(PPU_WR_N)
PPU_RX_OE_N = NOT(PPU_READ)
PPU_TX_OE_N = NOT(PPU_WRITE)
PPU_STATUS_EN = PPU_WRITE_BASE AND PPU_WR_N
PPU_STATUS_OE_N = NOT(PPU_STATUS_EN)
```

各CPU/PPU 8-bitレーンはデータ送受信とアドレスbyte書込みを共有するため、対応するADDR_STB中は両データ方向を必ずHi-Zにする。CPUではM2をL、CPU R/WをH、/ROMSELをHにし、PPUでは/RDと/WRをHに強制する。PPU status muxもPPU read・write・address strobeのすべてでHi-Zとし、PPU_RXと同じGP8–GP15を同時駆動しない。idle時だけstatus muxを有効にしてIRQ/CIRAM信号を入力レーンへ返す。SRAM OE_N/WE_NはそれぞれPPU_RX_OE_N/PPU_TX_OE_Nと同一ネットを共有する。読み書き競合、アドレス借用、リセットの排他条件は真理値表とKiCadネットリストで確認する。KiCad CLI ERC、PIO setup/hold、ロジアナ実測は未完了。

| 機能 | 候補IC |
| --- | --- |
| CPU Pico→cartridge | SN74AHCT244 ×1 |
| CPU cartridge→Pico | SN74LVC244A ×1 |
| PPU Pico→cartridge | SN74AHCT244 ×1 |
| PPU cartridge→Pico | SN74LVC244A ×1 |
| 5V制御信号（M2/RW/PPU /RD/PPU /WR//ROMSEL） | SN74AHCT244 ×1＋ゲート |

SN74AHCT244はVCC=4.5–5.5V時のVIH(min)=2.0V、入力最大5.5Vなので3.3V GPIOを受けられる。SN74LVC244AはVCC=1.65–3.6V、入力最大5.5V、Ioff対応。すべてのGPIOにカート側5Vを直結しない。

## 5. CIRAM相当RAMとFamicom端子

初号の内部CIRAM候補はAlliance Memory `AS6C6264-55PCN`（8K×8、55ns、2.7–5.5V、28-pin PDIP）。2KBのCIRAM相当領域としてA0–A9を保持PPU_A0–A9へ、A10をカート出力のCIRAM_A10(pin 18)へ接続し、SRAM A11/A12はGNDへ固定する。CIRAM_A10はカート側マッパーが内部CIRAMの1KBバンクを選ぶ信号であり、PPU_A10へ直結しない。PPUデータのカート側レーンにDQ0–DQ7を接続する。CE2(pin 26)は+5Vへ、CE#(pin 20)はカートからのCIRAM /CE(pin 48)へ接続する。

```text
SRAM_OE_N = PPU_RX_OE_N
SRAM_WE_N = PPU_TX_OE_N
```

したがって通常readではOE_N=0/WE_N=1、writeではOE_N=1/WE_N=0、idle・address-load・競合・resetでは両方HとなりSRAM出力／書込みを止める。SRAMのA0–A9は保持したPPUアドレス、A10はpin18 CIRAM_A10、CE#/OE#/WE#は上記のとおり。55ns SRAMの最悪値とAHCT/LVC伝搬時間を、実際のPPUサイクル内のデータセットアップ時間で照合する。

Famicom 60-pinコネクタの信号割当（NESdev表）：

| カート端子 | 接続 |
| --- | --- |
| 1, 16 | GND |
| 2–13 | CPU A11, A10, A9, A8, A7, A6, A5, A4, A3, A2, A1, A0 |
| 14 / 32 | CPU R/W / M2 |
| 15 | /IRQ入力（open-collector想定、弱いpull-up） |
| 17 / 47 | PPU /RD / PPU /WR |
| 18 / 48 | CIRAM A10 / CIRAM /CE |
| 19–25 | PPU A6–A0 |
| 26–29, 57–60 | PPU D0–D3, PPU D7–D4 |
| 30 | +5V_CART（保護・電流制限の後段） |
| 31 | NC。変種確認まで非接続 |
| 33–35 | CPU A12–A14 |
| 36–43 | CPU D7–D0 |
| 44 | /ROMSEL = NAND(M2, CPU A15) |
| 45 / 46 | Audio from 2A03 / Audio to RF |
| 49 / 56 | **PPU /A13 / PPU A13**。49は反転出力、56は非反転出力 |
| 50–55 | PPU A7–A12 |

pin49と56は同じネットではなく、pin49へA13反転を出す。pin31は未配線のままにする。

## 6. PPU入力ステータス多重化

受信したPPUデータと、カートから戻る低速状態信号を、PPU側GPIOレーン上で時間多重化する。SN74LVC257Aを2個使用する候補。A入力はPPU受信SN74LVC244Aの独立した8-bit出力`PPU_RX_D0–7`、B入力は`/IRQ`, `CIRAM_A10`, `CIRAM_CE_N`（残り5チャネルはGND）とし、MUX出力だけをGP8–GP15へ接続する。PPU受信244の出力をGPIOへ直結せず、MUXを唯一のGPIOドライバーとする。LVC257Aの入力は3.3V電源時にも最大5.5Vを受ける。

- SEL = PPU_RD_N（L:データ側A、H:待機時ステータス側B）
- OE_N = NOT(BUS_RUN) OR NOT(PPU_WR_N) OR PPU_ADDR_STB
- PPU read中はデータをPicoへ、idle中はステータスをPicoへ出す。
- write/address-strobe中はマルチプレクサ出力をHi-Zにし、Picoがデータを駆動しても衝突させない。
- `/IRQ`には弱いpull-upを設ける。CIRAM A10と/CEの既定値も抵抗で固定し、最終値は実装対象カートと測定で決める。

## 7. ADC・音声・電源

### ADC

GP26/ADC0はpin46音声returnを扱うアナログ入力。AC結合、1.65V付近のバイアス、減衰／クランプを含む前段を置き、ADCの0–3.3V範囲と電源断時の逆流を確認する。音声信号のピーク、DCバイアス、ソースインピーダンスを測るまでは前段の値を確定しない。

GP27/ADC1は`+5V_CART`の電圧監視候補（例：10k/10k分圧、1k直列、100nFフィルタなら5.5V時に約2.75V）。GP28/ADC2はアナログ予備入力／テストパッドとする。ADC入力はデジタルバスへ接続しない。

### 音声

GP22のPWMを低域フィルタしてpin45へ入れ、pin46から戻るカートリッジ音声をGP26でサンプルする構成候補。Famicomの拡張音声は2A03音声をカートリッジへ入力し、カート側で自身の音声と混合してreturnするため、この往復は必要。ただし音声振幅・バイアス・負荷条件の一次資料測定値をまだ得ていない。PWM周波数、フィルタ、減衰、出力バッファ、カップリング値は**保留**で、実カートとオシロスコープで決める。

### 電源・リセット

外部の安定化+5V入力から+5V_LOGICと、電流制限された+5V_CARTを分離する。Pico 2の3.3VはLVC系とADC前段に使う。電源のGNDは共通にする。pin30へは電流制限・逆流対策を通してのみ供給し、PicoのUSB VBUSと直結しない。

カートリッジ電源のenableはPicoの3.3V power-good／物理スイッチで管理し、`RUN_N`リセットで切らない。`RUN_N`はバス出力をHi-Zにして位相FFを初期化する用途に限定する。これはリセットを押してもカートリッジ側mapper stateとRAMを保持するため。起動時／電源断時のOEプルアップ、カート電源のinrush/current-limit値、ESD保護は次段で確定する。

## 8. 回路凍結の残条件

1. PIOでCPU/PPU 2バイトラッチ列を独立実行し、4種類の組合せ（CPU読/書、PPU読/書）と重複要求をロジアナで測る。
2. PPU 5.37 MHz相当のサイクルで`AS6C6264-55PCN`のread/write最悪タイミングとLVC/AHCT遅延の余裕を測る。
3. pin45/46の拡張音声信号レベルを実機カートで測り、PWMフィルタ、出力振幅、ADC保護・バイアスを決める。
4. 代表カートの+5V起動電流・定常電流を測り、eFuse/電源アダプタ/コネクタを決める。
5. 対象Pico 2モジュールを確定し、物理ピン番号、RESET/RUN_N、USB給電との分離、EEPROM/VSYS配線を照合する。
6. ESD、信号series抵抗、デカップリング、コネクタ物理適合を決めてからKiCadの製造用回路図・PCBへ移す。

## 参考資料

- Raspberry Pi Pico 2 / RP2350公式資料: https://pip.raspberrypi.com/documents/RP-008299-DS
- TI SN74AHCT573: https://www.ti.com/lit/ds/symlink/sn74ahct573.pdf
- TI SN74AHCT74: https://www.ti.com/lit/ds/symlink/sn74ahct74.pdf
- TI SN74AHCT244 (Rev.A fixed-direction 5-V buffer): https://www.ti.com/lit/ds/symlink/sn74ahct244.pdf
- TI SN74LVC244A (Rev.A fixed-direction 3.3-V/5-V-tolerant buffer): https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf
- TI SN74LVC257A: https://www.ti.com/lit/ds/symlink/sn74lvc257a.pdf
- Alliance Memory AS6C6264: https://www.alliancememory.com/wp-content/uploads/Alliance-Memory_64K_AS6C6264v2.0July2017.pdf
- NESdev Famicom cartridge connector: https://www.nesdev.org/wiki/Cartridge_connector
- NESdev expansion audio: https://www.nesdev.org/wiki/Category:Expansion_audio
