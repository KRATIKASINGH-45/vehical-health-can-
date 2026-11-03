/* ---------------------------------------------------------------------------
 * Vehicle Health Monitoring System Using CAN  -  TRANSMITTER NODE
 * Target : STM32F103C8T6 ("Blue Pill"), STM32CubeIDE + HAL, 72 MHz SYSCLK, APB1 = 36 MHz
 * Sensors: DHT11 (PA0), analog vibration sensor e.g. ADXL335 / piezo module (PA1 = ADC1_IN1),
 *          RPM pulse input (PB0, EXTI0, 1 pulse per crank revolution)
 * CAN    : CAN1 on PA11 (RX) / PA12 (TX) + TJA1050 / MCP2551 transceiver, 500 kbit/s
 * Frame  : identical to src/can_protocol.py  (see that file for the byte layout)
 *
 * STATUS : reference firmware written to mirror the Python software twin.  It has NOT been
 *          flashed or bench-tested in this submission - compile and calibrate on your board.
 * Cube settings: CAN1 Prescaler=4, BS1=13TQ, BS2=4TQ, SJW=1TQ (=> 36 MHz/(4*18) = 500 kbit/s),
 *          ADC1 IN1 single conversion, TIM2 free-running 1 MHz (PSC=71) for microsecond delays.
 * ------------------------------------------------------------------------- */
#include "main.h"
#include <string.h>

#define NODE_ID          0x101u          /* 0x101 engine, 0x102 transmission, 0x103 chassis */
#define TX_PERIOD_MS     1000u
#define ADC_SAMPLES      200u
#define ADC_ZERO_G_MV    1650.0f         /* ADXL335 at 3.3 V: 0 g = Vcc/2   (calibrate!)   */
#define ADC_MV_PER_G     330.0f          /* ADXL335 sensitivity ~330 mV/g                    */

extern CAN_HandleTypeDef hcan;
extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim2;
static volatile uint32_t rpm_pulses = 0;
static uint8_t seq = 0;

void HAL_GPIO_EXTI_Callback(uint16_t pin) { if (pin == GPIO_PIN_0) rpm_pulses++; }

static void delay_us(uint16_t us) { __HAL_TIM_SET_COUNTER(&htim2, 0); while (__HAL_TIM_GET_COUNTER(&htim2) < us); }

/* CRC-8, polynomial 0x07, init 0x00 (same as Python crc8()) */
static uint8_t crc8(const uint8_t *d, uint8_t n) {
    uint8_t c = 0;
    while (n--) { c ^= *d++; for (uint8_t i = 0; i < 8; i++) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1); }
    return c;
}

/* DHT11: returns 0 on success, temperature in whole degC (sensor resolution is 1 degC). */
static int dht11_read(int8_t *temp_c) {
    uint8_t d[5] = {0};
    GPIO_InitTypeDef g = {.Pin = GPIO_PIN_0, .Mode = GPIO_MODE_OUTPUT_OD, .Pull = GPIO_NOPULL, .Speed = GPIO_SPEED_FREQ_HIGH};
    HAL_GPIO_Init(GPIOA, &g); HAL_GPIO_WritePin(GPIOA, GPIO_PIN_0, 0); HAL_Delay(20);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_0, 1); delay_us(30);
    g.Mode = GPIO_MODE_INPUT; g.Pull = GPIO_PULLUP; HAL_GPIO_Init(GPIOA, &g);
    uint32_t t0 = HAL_GetTick();
    while (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0)) if (HAL_GetTick() - t0 > 2) return -1;
    while (!HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0)); while (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0));
    for (int i = 0; i < 40; i++) {
        while (!HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0)); delay_us(40);
        d[i / 8] = (uint8_t)((d[i / 8] << 1) | HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0));
        while (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0));
    }
    if ((uint8_t)(d[0] + d[1] + d[2] + d[3]) != d[4]) return -2;
    *temp_c = (int8_t)d[2]; return 0;
}

/* Vibration: RMS of the AC component over ~ADC_SAMPLES conversions, in milli-g. */
static uint16_t vibration_mg(void) {
    float sum = 0, sumsq = 0;
    for (uint32_t i = 0; i < ADC_SAMPLES; i++) {
        HAL_ADC_Start(&hadc1); HAL_ADC_PollForConversion(&hadc1, 5);
        float mv = HAL_ADC_GetValue(&hadc1) * 3300.0f / 4095.0f;
        float g = (mv - ADC_ZERO_G_MV) / ADC_MV_PER_G; sum += g; sumsq += g * g;
    }
    float mean = sum / ADC_SAMPLES, var = sumsq / ADC_SAMPLES - mean * mean;
    float rms = var > 0 ? sqrtf(var) : 0;
    return (uint16_t)(rms * 1000.0f);
}

static void send_frame(int16_t temp_dc, uint16_t vib_mg, uint16_t rpm) {
    uint8_t p[8];
    p[0] = temp_dc >> 8; p[1] = temp_dc & 0xFF; p[2] = vib_mg >> 8; p[3] = vib_mg & 0xFF;
    p[4] = rpm >> 8;     p[5] = rpm & 0xFF;     p[6] = seq++;        p[7] = crc8(p, 7);
    CAN_TxHeaderTypeDef h = {.StdId = NODE_ID, .IDE = CAN_ID_STD, .RTR = CAN_RTR_DATA, .DLC = 8};
    uint32_t mb;
    if (HAL_CAN_AddTxMessage(&hcan, &h, p, &mb) != HAL_OK) HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13); /* LED = TX error */
}

int main(void) {
    HAL_Init(); SystemClock_Config(); MX_GPIO_Init(); MX_ADC1_Init(); MX_CAN_Init(); MX_TIM2_Init();
    HAL_TIM_Base_Start(&htim2); HAL_CAN_Start(&hcan);
    uint32_t next = HAL_GetTick(); int8_t temp = 25;
    for (;;) {
        if ((int32_t)(HAL_GetTick() - next) >= 0) {
            next += TX_PERIOD_MS;
            uint32_t pulses = rpm_pulses; rpm_pulses = 0;           /* pulses per second */
            uint16_t rpm = (uint16_t)(pulses * 60u);                /* 1 pulse / rev     */
            int8_t t; if (dht11_read(&t) == 0) temp = t;            /* keep last good value on read error */
            send_frame((int16_t)temp * 10, vibration_mg(), rpm);
        }
    }
}
