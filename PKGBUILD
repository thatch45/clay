# Contributor: Thomas S Hatch <thatch45@gmail.com>

pkgname=clay
pkgver=0.7
pkgrel=1
pkgdesc="A KISS could controller and communication layer"
arch=(any)
url="http://beyondoblivion.com"
license=("GPL3")
depends=('python2'
         'certmaster'
         'func')
makedepends=()
optdepends=()
options=()
source=("$pkgname-$pkgver.tar.gz")
md5sums=('44957d7faabbe6dece7d8ddee5ac1af9')

package() {
  cd $srcdir/$pkgname-$pkgver

  python2 setup.py install --root=$pkgdir/ --optimize=1
}
