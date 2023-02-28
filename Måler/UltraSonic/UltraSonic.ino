#define trigPin 6
#define echoPin 7

void setup() {
Serial.begin (9600);
pinMode(trigPin, OUTPUT);
pinMode(echoPin, INPUT);
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

if (distance >= 2000 ) {
Serial.println("Out of range");
}
else {
Serial.print(distance);
Serial.println(" cm");
}
delay(500);
}