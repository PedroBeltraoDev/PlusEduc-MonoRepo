# População de dados para demonstração

Este documento descreve o seed reproduzível do ambiente local do PlusEduc. O objetivo é permitir uma apresentação completa do painel do professor e do portal do aluno sem versionar documentos do MongoDB, senhas, hashes, tokens ou dados pessoais.

## O que é versionado

O arquivo `PlusEduc-BE-Python/scripts/seed_demo_population.py` é idempotente e grava os dados diretamente no MongoDB local. Ele utiliza a marca `demo-population-2026` para reconhecer suas próprias inserções. A execução pode ser repetida sem multiplicar alunos, atividades, notas ou submissões do seed.

Os documentos reais do MongoDB permanecem locais e não são armazenados no Git. O seed pode ser executado em uma base local limpa ou sobre a base existente. Registros que não possuem a marca do seed são preservados, com exceção dos vínculos de matrícula necessários para garantir a regra de pelo menos cinco alunos por turma.

## Dados simulados

| Recurso | Resultado esperado no ambiente atual |
|---|---:|
| Alunos ativos | 77 |
| Turmas ativas de demonstração | 15 |
| Mínimo de alunos por turma | 5 |
| Atividades totais | 37 |
| Notas totais | 232 |
| Submissões totais | 98 |
| Questões discursivas pendentes | 32 |
| Questões discursivas revisadas | 60 |
| Questões objetivas corrigidas automaticamente | 138 |

A população cria duas atividades em cada turma: uma objetiva e uma discursiva. A participação é parcial para que a interface mostre alunos concluídos e pendentes. As submissões discursivas incluem respostas textuais, estados de revisão, feedback e identificação do professor quando já corrigidas.

Cada aluno recebe notas em três componentes curriculares, presença e, em uma parcela dos casos, lacunas de aprendizagem. Esses registros alimentam média individual, desempenho por turma, frequência e recomendações pedagógicas.

## Execução segura

A senha dos usuários locais deve ser informada somente por variável de ambiente. O repositório não contém uma senha padrão.

No PowerShell, a execução recomendada é:

```powershell
$env:PLUS_EDUC_DEMO_PASSWORD = "<senha-local-de-demonstracao>"
$env:MONGODB_URI = "mongodb://localhost:27017"
$env:MONGODB_DATABASE = "escola_db"
Set-Location "D:\PlusEducPython\PlusEduc\PlusEduc-BE-Python"
& ".\.venv\Scripts\python.exe" ".\scripts\seed_demo_population.py"
```

A lista privada de acessos deve permanecer fora do Git. Para a apresentação, use a lista entregue separadamente e não copie credenciais para issues, commits, capturas de tela ou documentação pública.

## Validação recomendada

Depois da execução, confirme no MongoDB que cada turma possui ao menos cinco membros, que cada aluno está em uma única turma e que as coleções `activities`, `grades` e `activity_submissions` contêm registros. Em seguida, valide pelo HTTP o login de professor, o desempenho de uma turma, o desempenho de um aluno, o portal do aluno e a lista de correções pendentes.

O endpoint de desempenho por turma e os endpoints de attendance individual devem ser usados conforme o OpenAPI atual. A existência de dados simulados não altera contratos, endpoints ou regras do backend.
