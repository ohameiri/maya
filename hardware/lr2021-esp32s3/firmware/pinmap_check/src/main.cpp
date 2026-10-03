// Pin map of the LR2021 + ESP32-S3 board (from the KiCad netlist), compiled to catch
// pin conflicts: SPI on the FSPI IOMUX pins, USB on GPIO19/20, PSRAM pins untouched.
#include <Arduino.h>
#include <SPI.h>

constexpr int PIN_LR_NSS = 10, PIN_LR_MOSI = 11, PIN_LR_SCK = 12, PIN_LR_MISO = 13;
constexpr int PIN_LR_NRESET = 14, PIN_LR_BUSY = 21, PIN_LR_IRQ = 47;   // IRQ = LR2021 DIO9
constexpr int PIN_LED_USER = 2, PIN_BOOT = 0;

static_assert(PIN_LR_IRQ != 35 && PIN_LR_IRQ != 36 && PIN_LR_IRQ != 37, "octal PSRAM pin");

SPIClass lrSpi(FSPI);
volatile bool irq = false;
void IRAM_ATTR onIrq() { irq = true; }

uint8_t lrCmd(uint16_t opcode) {          // LR2021 commands start with a 16-bit opcode
  while (digitalRead(PIN_LR_BUSY)) {}
  lrSpi.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_LR_NSS, LOW);
  uint8_t s = lrSpi.transfer(opcode >> 8);
  lrSpi.transfer(opcode & 0xff);
  digitalWrite(PIN_LR_NSS, HIGH);
  lrSpi.endTransaction();
  return s;
}

void setup() {
  Serial.begin(115200);                   // USB CDC on GPIO19/20
  pinMode(PIN_LED_USER, OUTPUT);
  pinMode(PIN_LR_NSS, OUTPUT); digitalWrite(PIN_LR_NSS, HIGH);
  pinMode(PIN_LR_NRESET, OUTPUT);
  pinMode(PIN_LR_BUSY, INPUT);
  pinMode(PIN_LR_IRQ, INPUT);
  attachInterrupt(PIN_LR_IRQ, onIrq, RISING);
  lrSpi.begin(PIN_LR_SCK, PIN_LR_MISO, PIN_LR_MOSI, PIN_LR_NSS);
  digitalWrite(PIN_LR_NRESET, LOW); delay(2); digitalWrite(PIN_LR_NRESET, HIGH); delay(10);
  Serial.printf("PSRAM %u bytes, LR2021 status 0x%02x\n", ESP.getPsramSize(), lrCmd(0x0101));
}

void loop() {
  digitalWrite(PIN_LED_USER, !digitalRead(PIN_LED_USER));
  delay(500);
}
