import subprocess
archive = set(subprocess.check_output(['git','ls-tree','-r','--name-only','github/master-archive-2025-12-04']).decode().splitlines())
research = set(subprocess.check_output(['git','ls-tree','-r','--name-only','github/research/optimization-integration']).decode().splitlines())
only_archive = sorted(list(archive - research))
only_research = sorted(list(research - archive))
print('Files only in master-archive (first 80):')
for f in only_archive[:80]:
    print(f)
print('\nCount only in archive:', len(only_archive))
print('\nFiles only in research (first 80):')
for f in only_research[:80]:
    print(f)
print('\nCount only in research:', len(only_research))
