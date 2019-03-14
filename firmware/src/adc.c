/* adc.c */

#include "adc.h"
#include "em_adc.h"
#include "em_cmu.h"

void adc_init(void)
{
    CMU_ClockEnable(cmuClock_ADC0, true);

    ADC_Init_TypeDef init_params = ADC_INIT_DEFAULT;
    init_params.timebase = ADC_TimebaseCalc(0);
    init_params.prescale = ADC_PrescaleCalc(1000000, 0);
    init_params.lpfMode = adcLPFilterBypass;
    init_params.ovsRateSel = adcOvsRateSel8;
    ADC_Init(ADC0, &init_params);

    ADC_InitSingle_TypeDef initsingle_params = ADC_INITSINGLE_DEFAULT;

    initsingle_params.acqTime = adcAcqTime16; /* XXX */
    initsingle_params.diff = false;
    initsingle_params.input = adcSingleInputCh6;
    initsingle_params.leftAdjust = false;
    initsingle_params.prsEnable = false;
    initsingle_params.prsSel = false;
    initsingle_params.reference = adcRef2V5;
    initsingle_params.rep = false;
    //initsingle_params.resolution = adcRes12Bit;
    initsingle_params.resolution = adcResOVS;
    
    ADC_InitSingle(ADC0, &initsingle_params);

}

uint16_t adc_read(void)
{
    ADC_Start(ADC0, adcStartSingle);

    while(!(ADC_IntGet(ADC0) & ADC_IF_SINGLE))
        ;

    ADC_IntClear(ADC0, ADC_IF_SINGLE);

    return ADC_DataSingleGet(ADC0);
}

