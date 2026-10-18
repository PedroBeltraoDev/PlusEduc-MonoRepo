// Estatísticas por grupo sobre notas: redução segmentada, um work-group por grupo.
//
// Os registros chegam ordenados por grupo e `offsets` (n_groups + 1 posições) delimita cada segmento,
// como no formato CSR. Cada work-item acumula uma fatia do segmento em registradores e o work-group
// combina as parciais numa árvore em memória local (com barrier), sem operações atômicas: o resultado
// não depende da ordem de execução das threads.
#pragma OPENCL EXTENSION cl_khr_fp64 : enable

#define NO_STAMP LONG_MIN

__kernel void grade_stats(
    __global const double *values,      // nota de cada registro
    __global const char   *attendance,  // -1 sem registro de presença, 0 faltou, 1 presente
    __global const long   *stamps,      // data em microssegundos desde 1970 (NO_STAMP = sem data)
    __global const int    *offsets,     // início de cada segmento; offsets[n_groups] = total
    __global double       *out_sum,
    __global int          *out_count,
    __global int          *out_recorded,
    __global int          *out_attended,
    __global long         *out_last,
    __local  double       *l_sum,
    __local  int          *l_recorded,
    __local  int          *l_attended,
    __local  long         *l_last)
{
    const int group = get_group_id(0);
    const int lid = get_local_id(0);
    const int lsize = get_local_size(0);  // potência de 2 (garantido pelo host)
    const int begin = offsets[group];
    const int end = offsets[group + 1];

    double sum = 0.0;
    int recorded = 0, attended = 0;
    long last = NO_STAMP;
    for (int i = begin + lid; i < end; i += lsize) {
        sum += values[i];
        const char a = attendance[i];
        if (a >= 0) {
            recorded += 1;
            attended += a;
        }
        last = max(last, stamps[i]);
    }

    l_sum[lid] = sum;
    l_recorded[lid] = recorded;
    l_attended[lid] = attended;
    l_last[lid] = last;
    barrier(CLK_LOCAL_MEM_FENCE);

    for (int stride = lsize / 2; stride > 0; stride >>= 1) {
        if (lid < stride) {
            l_sum[lid] += l_sum[lid + stride];
            l_recorded[lid] += l_recorded[lid + stride];
            l_attended[lid] += l_attended[lid + stride];
            l_last[lid] = max(l_last[lid], l_last[lid + stride]);
        }
        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (lid == 0) {
        out_sum[group] = l_sum[0];
        out_count[group] = end - begin;
        out_recorded[group] = l_recorded[0];
        out_attended[group] = l_attended[0];
        out_last[group] = l_last[0];
    }
}
