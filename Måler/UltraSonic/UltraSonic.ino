#include <SigFox.h>
#include <ArduinoLowPower.h>

#define trigPin 6
#define echoPin 7

void setup() {
  Serial.begin (9600);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  while (!Serial) {};
  if (!SigFox.begin()) {
      Serial.println("Shield error or not present!");
      return;
  }
  // Enable debug LED and disable automatic deep sleep
  // Comment this line when shipping your project :)
  SigFox.debug();
  delay(100);
  SigFox.end();
}

void loop() {
  long duration, distance;
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  duration = pulseIn(echoPin, HIGH);    // Måler hvor lang tid pulsen er HØJ
  distance = (duration/2) / 29.1;       // Lydens hastighed. 29.1 cm pr. microsekund.

  
  String myMessage = String(distance) + ":cm";
  myMessage.trim();

  Serial.println(myMessage);
  sendString(myMessage);
  
  delay(10000);
}

void sendString(String str) {
  SigFox.begin();   // Start the module
  delay(100);       // Wait at least 30mS after first configuration (100mS before)
  SigFox.status();  // Clears all pending interrupts
  delay(1);

  SigFox.beginPacket();
  SigFox.print(str);

  int ret = SigFox.endPacket();  // send buffer to SIGFOX network
  Serial.println(ret);
  if (ret > 0) {
    Serial.println("No transmission");
  } else {
    Serial.println("Transmission ok");
  }
  Serial.println(SigFox.status(SIGFOX));
  Serial.println(SigFox.status(ATMEL));
  SigFox.end();
}