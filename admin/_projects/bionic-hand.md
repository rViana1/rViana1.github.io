---
title:
  en: Bionic Hand
  pt: Mão Biónica
subtitle:
  en: Arduino prototype
  pt: Protótipo com Arduino
summary:
  en: An Arduino-based bionic hand prototype that I designed, assembled and programmed.
  pt: Protótipo de mão biónica com Arduino, que concebi, montei e programei.
order: 2
project_order: 3
tags: [prototype]
cover: /images/projects/bionic-hand/cover.webp
cover_width: 1080
cover_height: 1440
tech: [Arduino Uno, C++, MyoWare, Servo Shield, PWM, Servomotors]
highlights:
  - en: Assembled and programmed a hand controlled by muscle activity.
    pt: Montagem e programação de uma mão controlada pela atividade muscular.
  - en: Connected a muscle sensor to servomotors that move the fingers using nylon thread.
    pt: Ligação de um sensor muscular a servomotores que movem os dedos através de fios de nylon.
links:
  - label:
      en: Watch project video
      pt: Ver vídeo do projeto
    url: https://youtu.be/CemfhXgntak?si=8L10qFcEmOQcol-h
---
I assembled and programmed this Arduino-based bionic hand as a vocational school project, bringing together electronics, mechanical assembly and software.

## How it works

A MyoWare muscle sensor detects electrical activity during muscle contraction and sends an analogue signal to an Arduino Uno. The program reads that signal and, according to defined thresholds, instructs the servomotors to open or close the hand.

An Adafruit Servo Shield controls the motors using PWM signals. Nylon threads connect the motors to the fingers, translating their rotation into movement. The prototype required testing and adjustments to the mechanical assembly and sensor readings, which were affected by electrical interference.

<!--pt-->

Montei e programei este protótipo de mão biónica com Arduino como projeto do ensino profissional, conjugando eletrónica, montagem mecânica e programação.

## Como funciona

Um sensor muscular MyoWare deteta a atividade elétrica durante a contração muscular e envia um sinal analógico para um Arduino Uno. O programa lê esse sinal e, de acordo com limiares definidos, comanda os servomotores para abrir ou fechar a mão.

Um Adafruit Servo Shield controla os motores através de sinais PWM. Fios de nylon ligam os motores aos dedos, transformando a sua rotação em movimento. O protótipo exigiu testes e ajustes à montagem mecânica e às leituras do sensor, que eram afetadas por interferências elétricas.
