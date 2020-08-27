/* WALL-E ANIMATION PRESETS
 ********************************************
 * Code by: Simon Bluett
 * Email:   hello@chillibasket.com
 * Version: 2.7
 * Date:    7th August 2020
 ********************************************
 * 
 * - Preset animations for all the servo motors can be defined here.
 * - The animations consist of a set of position instructions for each
 *   servo motor, along with a specified time for how long that position
 *   should be held until the next animation instruction is executed.
 *
 * - To add your own animation, follow these steps:
 *   1. Add a new 'case' statement with the number you want to associate with your animation.
 *   2. Follow the same format as below to add new movement instructions
 *      queue.push({time, head rotation, neck top, neck bottom, eye right, eye left, arm left, arm right})
 *      > The time needs to be a number in milliseconds
 *      > Each servo position value needs to be an integer (whole) number between 0-100
 *      > 0 = LOW servo position, 100 = HIGH servo position as specified in the wall-e_calibration sketch
 *      > If you want the servo to be disabled/not updated by a specific instruction, use -1
 *   3. Make sure that your 'case' statement ends with the "break;" command 
 */

#ifndef ANIMATIONS_INO
#define ANIMATIONS_INO

void playAnimation(int animationNo) {

	switch (animationNo) {

		case 0:
			// --- Reset Servo positions ---
			//			time,head,necT,necB,eyeR,eyeL,armL,armR
			queue.push({1000,  50,  10,  0,   0,   0,  40,  40});
			break;

		case 1:
			// --- Bootup Eye Sequence ---
			//			time,head,necT,necB,eyeR,eyeL,armL,armR
			queue.push({2000,  50,  45,  90,  40,  40,  40,  40});
			queue.push({ 700,  50,  45,  90,  40,   0,  40,  40});
			queue.push({ 700,  50,  45,  90,   0,   0,  40,  40});
			queue.push({ 700,  50,  45,  90,   0,  40,  40,  40});
			queue.push({ 700,  50,  45,  90,  40,  40,  40,  40});
			queue.push({ 400,  50,  45,  90,   0,   0,  40,  40});
			queue.push({ 400,  50,  45,  90,  40,  40,  40,  40});
			queue.push({2000,  50,   0,  60,  40,  40,  40,  40});
			queue.push({1000,  50,   0,  60,   0,   0,  40,  40});
			break;

		case 2:
			// --- Inquisitive motion sequence ---
			//			time,head,necT,necB,eyeR,eyeL,armL,armR
			queue.push({3000,  48,  40,   0,  35,  45,  60,  59});
			queue.push({1151,  48,  40,  20, 100,   0,  80,  80});
			queue.push({3000,   0,  40,  40, 100,   0,  80,  80});
			queue.push({1151,  48,  60, 100,  40,  40, 100, 100});
			queue.push({1151,  48,  40,  30,  45,  35,   0,   0});
			queue.push({1151,  34,  34,  10,  14, 100,   0,   0});
			queue.push({1151,  48,  60,  20,  35,  45,  60,  59});
			queue.push({3000, 100,  20,  50,  40,  40,  60, 100});
			queue.push({1151,  48,  15,   0,   0,   0,   0,   0});
			queue.push({1000,  50,  10,   0,   0,   0,  40,  40});
			break;

		case 3:
			// --- Dance smooth ---
			//			    time, head,necT,necB,eyeR,eyeL,armL,armR
      queue.push({1000,  0,  40,   0,  35,  45,  60,  50});
      queue.push({1000,  20, 60,   0,  35,  45,  40,  70});
      queue.push({1000,  0,  60,   0,  35,  45,  60,  50});
      queue.push({1000,  20, 40,   0,  35,  45,  40,  70});
      queue.push({1000,  30,  40,   50,  35,  45,  60,  50});
      queue.push({1000,  20, 40,   50,  35,  45,  40,  70});
      queue.push({1000,  30,  40,   50,  35,  45,  60,  55});
      queue.push({1000,  20, 40,   50,  35,  45,  40,  75});
      queue.push({1000,  40,  60,   100,  35,  45,  60,  60});
      queue.push({1000,  30, 60,   100,  35,  45,  40,  80});
      queue.push({1000,  20,  40,   100,  35,  45,  60,  55});
      queue.push({1000,  10, 40,   100,  35,  45,  40,  75});
      queue.push({1000,  20, 60,   0,  35,  45,  40,  70});
      queue.push({1000,  0,  40,   0,  35,  45,  60,  50});
      queue.push({1000,  40,  60,   100,  35,  45,  60,  60});
      queue.push({1000,  30, 60,   100,  35,  45,  40,  80});
      queue.push({1000,  20,  40,   100,  35,  45,  60,  55});
      queue.push({1000,  10, 40,   100,  35,  45,  40,  75});
      queue.push({1000,  20, 60,   0,  35,  45,  40,  70});
      queue.push({1000,  0,  60,   0,  35,  45,  60,  50});
      queue.push({1000,  20, 40,   0,  35,  45,  40,  70});
      queue.push({1000,  30,  40,   50,  35,  45,  60,  50});
      queue.push({1000,  20, 40,   50,  35,  45,  40,  70});
      queue.push({1000,  30,  40,   50,  35,  45,  60,  55});
      queue.push({1000,  20, 40,   50,  35,  45,  40,  75});
      queue.push({1000,  40,  60,   100,  35,  45,  60,  60});
      queue.push({1000,  30, 60,   100,  35,  45,  40,  80});
      queue.push({1000,  20,  40,   100,  35,  45,  60,  55});
      queue.push({1000,  10, 40,   100,  35,  45,  40,  75});
      queue.push({1000,  20, 60,   0,  35,  45,  40,  70});
			
			break;
    case 4:
      //          time, head,necT,necB,eyeR,eyeL,armL,armR
      queue.push({151,  100, 0,   0,    35,  45,  0,  0});
      queue.push({151,  90,  20,    10,  35,  45,  10,  10});
      queue.push({151,  80,  40,    20,  35,  45,  20,  20});
      queue.push({151,  70,  40,    30,  35,  45,  30,  30});
      queue.push({151,  60,  40,    40,  35,  45,  40,  40});
      queue.push({151,  50,  40,    50,  35, 45,  50,  50});
      queue.push({151,  40,  40,   60,  35,  45,  60,  60});
      queue.push({151,  50,  40,   70,  35,  45,  70,  70});
      queue.push({151,  50,  40,   80,  35,  45,  80,  80});
      queue.push({151,  50,  40,   90,  35,  45,  90,  90});
      queue.push({4000,  50,   40,   100,  35,  45,  100, 100});
    case 5:
      queue.push({151,  10,  80,   90,  35,  45,  90,  90});
      queue.push({151,  20,  80,   80,  35,  45,  80,  80});
      queue.push({151,  30,  80,   70,  35,  45,  70,  70});
      queue.push({151,  40,  80,   60,  35,  45,  60,  60});
      queue.push({151,  50,  80,    50,  35,  45,  50,  50});
      queue.push({151,  50,  80,    40,  35,  45,  40,  40});
      queue.push({151,  50,  80,    30,  35,  45,  30,  30});
      queue.push({151,  50,  80,    20,  35,  45,  20,  20});
      queue.push({151,  50,  80,    10,  35,  45,  10,  10});
      queue.push({151,  50,  80,   0,  35,  45,  0,  0});
      
      break;
		default:
			Serial.println(F("Invalid animation requested"));
			break;
	}


}


#endif /* ANIMATIONS_CPP */
