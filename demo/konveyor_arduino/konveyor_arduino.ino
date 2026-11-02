// KARTA - konveyor mini untuk demo TKT 4
// Perangkat: Arduino Uno/Nano, driver motor BTS7960 atau L298N, motor DC gearbox 12 V,
// servo MG996R (pengalih rute), sensor IR halangan (FC-51) di bawah kamera.
// Protokol serial 115200: "JALAN <0-255>", "STOP", "RUTE U|B|M|R". Balasan "OK ...".
#include <Servo.h>

const int PIN_PWM = 5;      // ke RPWM BTS7960 / ENA L298N
const int PIN_DIR = 4;      // ke IN1 L298N (BTS7960: LPWM ke GND)
const int PIN_SERVO = 9;
const int PIN_IR = 2;       // aktif LOW saat ada benda

// sudut servo per rute; sesuaikan dengan posisi corong/bak di rangka konveyor
const int SUDUT_U = 20;     // umpan langsung
const int SUDUT_B = 70;     // bio-drying
const int SUDUT_M = 110;    // maggot BSF
const int SUDUT_R = 160;    // residu

Servo pengalih;
String buf;
bool irSebelum = HIGH;
unsigned long tTerakhirBenda = 0;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PWM, OUTPUT);
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_IR, INPUT_PULLUP);
  digitalWrite(PIN_DIR, HIGH);
  analogWrite(PIN_PWM, 0);
  pengalih.attach(PIN_SERVO);
  pengalih.write(SUDUT_R);
  Serial.println("OK SIAP");
}

void prosesPerintah(String c) {
  c.trim();
  if (c.startsWith("JALAN")) {
    int v = constrain(c.substring(6).toInt(), 0, 255);
    analogWrite(PIN_PWM, v);
    Serial.print("OK JALAN "); Serial.println(v);
  } else if (c == "STOP") {
    analogWrite(PIN_PWM, 0);
    Serial.println("OK STOP");
  } else if (c.startsWith("RUTE")) {
    char r = c.charAt(5);
    int s = (r == 'U') ? SUDUT_U : (r == 'B') ? SUDUT_B : (r == 'M') ? SUDUT_M : SUDUT_R;
    pengalih.write(s);
    Serial.print("OK RUTE "); Serial.println(r);
  } else {
    Serial.println("ERR perintah tidak dikenal");
  }
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { prosesPerintah(buf); buf = ""; }
    else buf += ch;
  }
  // kirim "BENDA" sekali saat sensor berubah dari kosong ke ada benda (debounce 500 ms)
  bool ir = digitalRead(PIN_IR);
  if (irSebelum == HIGH && ir == LOW && millis() - tTerakhirBenda > 500) {
    Serial.println("BENDA");
    tTerakhirBenda = millis();
  }
  irSebelum = ir;
}
