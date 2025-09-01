import 'package:flutter/material.dart';

class PhotoBox extends StatelessWidget {
  final String photoPath;
  final bool isNetwork;

  const PhotoBox({required this.photoPath, this.isNetwork = false, super.key});

  @override
  Widget build(BuildContext context) {
    final imageProvider = isNetwork
        ? NetworkImage(photoPath)
        : AssetImage(photoPath) as ImageProvider;
    return Center(
      child: GestureDetector(
        onTap: () {
          showDialog(
            context: context,
            builder: (BuildContext context) {
              return Dialog(
                backgroundColor: Colors.black.withOpacity(0.8), // 어두운 배경
                insetPadding: const EdgeInsets.all(0), // 여백 제거
                child: Stack(
                  children: [
                    Center(
                      child: InteractiveViewer(
                        // 줌, 드래그 허용
                        child: AspectRatio(
                          aspectRatio: 1, // 정사각형 비율 유지
                          child: Image(
                            image: imageProvider,
                            fit: BoxFit.contain,
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      top: 40,
                      right: 20,
                      child: IconButton(
                        icon: const Icon(
                          Icons.close,
                          color: Colors.white,
                          size: 36,
                        ),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ),
                  ],
                ),
              );
            },
          );
        },
        child: Container(
          width: 375,
          height: 375,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.15),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
            image: DecorationImage(image: imageProvider, fit: BoxFit.cover),
          ),
        ),
      ),
    );
  }
}