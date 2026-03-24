/*--------------------------------------------------------------------------*/
//
// WIN32 must be defined when compiling for Windows.
// For Visual C++ this is normally already defined.
//
// Copyright (C) 2000, 5DT <Fifth Dimension Technologies>
/*--------------------------------------------------------------------------*/

#include <stdio.h>    
#include <string.h>   
#include <stdarg.h>   

#ifdef WIN32
#include <windows.h>  

#else
#include <unistd.h>   
#include <time.h>     
#endif


#include "..\..\fglove.h" 

// função auxiliar para logs/mensagens de status
void print_log(const char* format, ...) {
    va_list args;
    va_start(args, format);
    vfprintf(stderr, format, args); 
    va_end(args);
    fflush(stderr); 
}


int main(int argc, char** argv)
{
    
    char* szPort = NULL;
    char	szPortToOpen[6];
    fdGlove* pGlove = NULL;
    
    bool showraw = false;
    int glovetype = FD_GLOVENONE;
    int i;

   
    int calibration_duration_s = 15;

    // tratamento de argumentos de linha de comando
    if (argc < 2)
    {
        print_log("Uso: %s <devicename>\n", argv[0]);
        print_log("Exemplo: %s USB0 ou %s COM1\n", argv[0], argv[0]);
        print_log("\nUsando porta padrao: USB0\n"); 
        strcpy(szPortToOpen, "USB0"); 
    }
    else
    {
        strncpy(szPortToOpen, argv[1], sizeof(szPortToOpen) - 1);
        szPortToOpen[sizeof(szPortToOpen) - 1] = '\0'; 
    }

    // --- CONEXÃO COM A LUVA ---
    print_log("Tentando abrir a luva na %s .. ", szPortToOpen);
    if (NULL == (pGlove = fdOpen(szPortToOpen)))
    {
        print_log("falhou. Certifique-se de que o GloveManager esta fechado e a luva conectada.\n"); 
    }
    print_log("sucesso.\n");

    print_log("Tipo de luva: %d\n", fdGetGloveType(pGlove));
    print_log("Mao: %s\n", fdGetGloveHand(pGlove) == FD_HAND_RIGHT ? "Direita" : "Esquerda"); 
    print_log("Numero de sensores: %d\n", fdGetNumSensors(pGlove));

    // --- FASE DE AUTO-CALIBRAÇÃO ---
    print_log("\n--- INICIO DA CALIBRACAO AUTOMATICA ---\n"); 
    print_log("Por favor, abra e feche a mao com a maior amplitude possivel por %d segundos.\n", calibration_duration_s); // Sem acentos
    print_log("Faca movimentos rapidos e completos de abrir e fechar a mao.\n"); 
    fdSetAutoCalibrate(pGlove, true); // ativa auto-calibração

#ifdef WIN32
    ULONGLONG start_cal_time_ms = GetTickCount64();
    ULONGLONG current_time_ms;
#else 
    time_t start_cal_time = time(NULL);
#endif

    int last_printed_s = calibration_duration_s + 1;

    while (1) {
#ifdef WIN32
        current_time_ms = GetTickCount64();
        int elapsed_s = (int)((current_time_ms - start_cal_time_ms) / 1000);
#else
        int elapsed_s = (int)(time(NULL) - start_cal_time);
#endif

        if (elapsed_s >= calibration_duration_s) {
            break; // sai do loop de calibração
        }

        int remaining_s = calibration_duration_s - elapsed_s;
        if (remaining_s < last_printed_s) { // imprime a cada segundo que muda
            print_log("\rCalibrando... %ds restantes  ", remaining_s);
            last_printed_s = remaining_s;
        }

        int packet_rate = fdGetPacketRate(pGlove);
        if (packet_rate <= 0) {
            packet_rate = 60; // padrão 60 Hz
        }
#ifdef WIN32
        Sleep(1000 / packet_rate);
#else
        usleep(1000000 / packet_rate); // usleep em microssegundos
#endif
    }
    print_log("\nCalibracao Concluida! Limites de movimento definidos para o paciente.\n"); 
    fdSetAutoCalibrate(pGlove, false); // desativa auto-calibração


    // --- LOOP DE DETECÇÃO E ENVIO DE DADOS PARA PROHRAMA EM PYTHON ---
    print_log("\n--- INICIO DA DETECCAO EM TEMPO REAL ---\n"); 
    print_log("Enviando IDs de gesto para Python. Pressione Ctrl+C na janela do Python para sair.\n"); 

    int packet_rate = fdGetPacketRate(pGlove);
    if (packet_rate <= 0) {
        packet_rate = 60;
    }

    // array para armazenar todos os valores escalonados dos sensores (18 sensores)
    float scaled_values[18];

    while (1) 
    {
        // obtém todos os valores escalonados dos sensores
        fdGetSensorScaledAll(pGlove, scaled_values);

        // obtém o ID do gesto
        int gesture_id = fdGetGesture(pGlove); //

        // imprime o ID do gesto e todos os valores dos sensores em uma única linha
        // formato: <gesture_id>,<sensor_0>,<sensor_1>,...,<sensor_17>
        printf("%d", gesture_id);
        for (int j = 0; j < 18; j++) {
            printf(",%.3f", scaled_values[j]);
        }
        printf("\n");
        fflush(stdout); 

        // pausa para controlar a taxa de amostragem
        #ifdef WIN32
        Sleep(1000 / packet_rate);
        #else
        usleep(1000000 / packet_rate);
        #endif
    }

    // --- FECHAMENTO DA LUVA --- 
    print_log("Fechando a luva.\n"); 
    fdClose(pGlove);
    print_log("Luva fechada. Adeus!\n"); 

    return 0;
}