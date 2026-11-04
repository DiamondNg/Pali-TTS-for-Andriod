// Read Pāli Aloud: 16-bit mono samples → MP3 with LAME (called from Mp3.kt).
// Copyright (C) 2026 Āyasmā Paññādhammika — AGPL-3.0-or-later (see LICENSE).
#include <jni.h>
#include <stdint.h>
#include "lame.h"

JNIEXPORT jlong JNICALL
Java_io_github_diamondng_readpalialoud_Mp3_open(JNIEnv *env, jclass cls, jint rate, jint kbps) {
    lame_t l = lame_init();
    if (!l) return 0;
    lame_set_in_samplerate(l, rate);
    lame_set_out_samplerate(l, rate);
    lame_set_num_channels(l, 1);
    lame_set_mode(l, MONO);
    lame_set_brate(l, kbps);
    lame_set_quality(l, 5);
    if (lame_init_params(l) < 0) { lame_close(l); return 0; }
    return (jlong)(intptr_t)l;
}

/* Encodes n samples; returns the number of MP3 bytes written to out (negative: error). */
JNIEXPORT jint JNICALL
Java_io_github_diamondng_readpalialoud_Mp3_encode(JNIEnv *env, jclass cls, jlong h,
                                                  jshortArray pcm, jint n, jbyteArray out) {
    jshort *s = (*env)->GetShortArrayElements(env, pcm, NULL);
    jbyte *o = (*env)->GetByteArrayElements(env, out, NULL);
    int r = lame_encode_buffer((lame_t)(intptr_t)h, s, s, n, (unsigned char *)o,
                               (*env)->GetArrayLength(env, out));
    (*env)->ReleaseShortArrayElements(env, pcm, s, JNI_ABORT);
    (*env)->ReleaseByteArrayElements(env, out, o, 0);
    return r;
}

JNIEXPORT jint JNICALL
Java_io_github_diamondng_readpalialoud_Mp3_flush(JNIEnv *env, jclass cls, jlong h, jbyteArray out) {
    jbyte *o = (*env)->GetByteArrayElements(env, out, NULL);
    int r = lame_encode_flush((lame_t)(intptr_t)h, (unsigned char *)o,
                              (*env)->GetArrayLength(env, out));
    (*env)->ReleaseByteArrayElements(env, out, o, 0);
    return r;
}

JNIEXPORT void JNICALL
Java_io_github_diamondng_readpalialoud_Mp3_close(JNIEnv *env, jclass cls, jlong h) {
    lame_close((lame_t)(intptr_t)h);
}
